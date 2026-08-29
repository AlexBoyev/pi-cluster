import logging
import re
from datetime import datetime, timezone
from typing import Any

import yaml
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.config import settings
from app.schemas.workload import NodeCapacity

logger = logging.getLogger(__name__)

_CPU_RE = re.compile(r"^(\d+)m$")
_MEM_RE = re.compile(r"^(\d+)(Ki|Mi|Gi)$")


def _parse_cpu_m(cpu: str) -> int:
    m = _CPU_RE.match(cpu)
    if m:
        return int(m.group(1))
    try:
        return int(cpu) * 1000
    except ValueError:
        return 0


def _parse_mem_mi(mem: str) -> int:
    m = _MEM_RE.match(mem)
    if not m:
        return 0
    val, unit = int(m.group(1)), m.group(2)
    if unit == "Ki":
        return val // 1024
    if unit == "Gi":
        return val * 1024
    return val


def _load_api() -> client.ApiClient:
    with open(settings.k8s_kubeconfig_path) as f:
        kube_cfg = yaml.safe_load(f)
    for cluster in kube_cfg.get("clusters", []):
        server: str = cluster["cluster"].get("server", "")
        if "127.0.0.1" in server or "localhost" in server:
            port = server.rsplit(":", 1)[-1]
            cluster["cluster"]["server"] = f"https://{settings.k8s_api_host}:{port}"
    config.load_kube_config_from_dict(kube_cfg)
    return client.ApiClient()


class K8sService:
    def _apps(self) -> client.AppsV1Api:
        return client.AppsV1Api(_load_api())

    def _core(self) -> client.CoreV1Api:
        return client.CoreV1Api(_load_api())

    def _storage(self) -> client.StorageV1Api:
        return client.StorageV1Api(_load_api())

    def _networking(self) -> client.NetworkingV1Api:
        return client.NetworkingV1Api(_load_api())

    def create_deployment(
        self,
        name: str,
        namespace: str,
        image: str,
        replicas: int,
        target_node: str | None,
        cpu_request: str,
        memory_request: str,
        env_vars: dict[str, str] | None = None,
        cpu_limit: str = "500m",
        memory_limit: str = "256Mi",
        liveness_path: str | None = None,
        readiness_path: str | None = None,
        probe_port: int | None = None,
    ) -> None:
        node_selector = {"kubernetes.io/hostname": target_node} if target_node else None
        env = [client.V1EnvVar(name=k, value=v) for k, v in env_vars.items()] if env_vars else None
        liveness_probe = None
        readiness_probe = None
        if probe_port:
            if liveness_path:
                liveness_probe = client.V1Probe(
                    http_get=client.V1HTTPGetAction(path=liveness_path, port=probe_port),
                    initial_delay_seconds=15, period_seconds=10, failure_threshold=3,
                )
            if readiness_path:
                readiness_probe = client.V1Probe(
                    http_get=client.V1HTTPGetAction(path=readiness_path, port=probe_port),
                    initial_delay_seconds=5, period_seconds=10, failure_threshold=3,
                )
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        node_selector=node_selector,
                        containers=[
                            client.V1Container(
                                name=name,
                                image=image,
                                env=env,
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": cpu_request, "memory": memory_request},
                                    limits={"cpu": cpu_limit, "memory": memory_limit},
                                ),
                                liveness_probe=liveness_probe,
                                readiness_probe=readiness_probe,
                            )
                        ],
                    ),
                ),
            ),
        )
        self._apps().create_namespaced_deployment(namespace=namespace, body=deployment)

    def update_deployment_probes(
        self, name: str, namespace: str,
        liveness_path: str | None, readiness_path: str | None, probe_port: int,
    ) -> None:
        def _probe(path: str | None) -> dict | None:
            if not path:
                return None
            return {"httpGet": {"path": path, "port": probe_port}, "initialDelaySeconds": 15, "periodSeconds": 10, "failureThreshold": 3}

        self._apps().patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": [{
                "name": name,
                "livenessProbe": _probe(liveness_path),
                "readinessProbe": _probe(readiness_path),
            }]}}}},
        )

    def update_deployment_resources(self, name: str, namespace: str, cpu_limit: str, memory_limit: str) -> None:
        self._apps().patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": [{
                "name": name,
                "resources": {"limits": {"cpu": cpu_limit, "memory": memory_limit}},
            }]}}}},
        )

    def update_deployment_env(self, name: str, namespace: str, env_vars: dict[str, str]) -> None:
        env = [{"name": k, "value": v} for k, v in env_vars.items()]
        self._apps().patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": [{"name": name, "env": env}]}}}},
        )

    def delete_deployment(self, name: str, namespace: str) -> None:
        self._apps().delete_namespaced_deployment(name=name, namespace=namespace)

    def get_ready_replicas(self, name: str, namespace: str) -> int:
        try:
            dep = self._apps().read_namespaced_deployment(name=name, namespace=namespace)
            return dep.status.ready_replicas or 0
        except ApiException:
            return 0

    def get_node_capacities(self) -> list[NodeCapacity]:
        core = self._core()
        nodes = core.list_node()
        pods = core.list_pod_for_all_namespaces()

        requests_per_node: dict[str, dict[str, int]] = {}
        for pod in pods.items:
            node_name = pod.spec.node_name
            if not node_name:
                continue
            bucket = requests_per_node.setdefault(node_name, {"cpu": 0, "mem": 0})
            for container in pod.spec.containers:
                if container.resources and container.resources.requests:
                    reqs = container.resources.requests
                    bucket["cpu"] += _parse_cpu_m(reqs.get("cpu", "0"))
                    bucket["mem"] += _parse_mem_mi(reqs.get("memory", "0"))

        capacities: list[NodeCapacity] = []
        for node in nodes.items:
            name = node.metadata.name
            alloc = node.status.allocatable or {}
            reqs = requests_per_node.get(name, {"cpu": 0, "mem": 0})
            ready = any(
                c.type == "Ready" and c.status == "True"
                for c in (node.status.conditions or [])
            )
            capacities.append(NodeCapacity(
                node_name=name,
                cpu_allocatable_m=_parse_cpu_m(alloc.get("cpu", "0")),
                cpu_requested_m=reqs["cpu"],
                memory_allocatable_mi=_parse_mem_mi(alloc.get("memory", "0")),
                memory_requested_mi=reqs["mem"],
                ready=ready,
                schedulable=not (node.spec.unschedulable or False),
            ))
        return capacities

    def pick_best_node(self) -> str | None:
        caps = self.get_node_capacities()
        eligible = [c for c in caps if c.ready and c.schedulable]
        if not eligible:
            return None
        return max(eligible, key=lambda c: c.cpu_allocatable_m - c.cpu_requested_m).node_name

    def scale_deployment(self, name: str, namespace: str, replicas: int) -> None:
        self._apps().patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"replicas": replicas}},
        )

    def get_workload_events(self, name: str, namespace: str) -> list:
        core = self._core()
        all_events = core.list_namespaced_event(namespace)
        events = [
            e for e in all_events.items
            if e.involved_object.name == name
            or (e.involved_object.name or "").startswith(name + "-")
        ]
        events.sort(key=lambda e: e.last_timestamp or 0, reverse=True)
        return events[:50]

    def update_deployment_image(self, name: str, namespace: str, image: str) -> None:
        self._apps().patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": [{"name": name, "image": image}]}}}},
        )

    def get_pod_list(self, name: str, namespace: str) -> list:
        return self._core().list_namespaced_pod(namespace=namespace, label_selector=f"app={name}").items

    def get_pod_logs(self, name: str, namespace: str, tail_lines: int = 100) -> tuple[str, str]:
        core = self._core()
        pods = core.list_namespaced_pod(namespace=namespace, label_selector=f"app={name}")
        if not pods.items:
            raise ValueError(f"No pods found for deployment {name}")
        pod = next(
            (p for p in pods.items if p.status.phase == "Running"),
            pods.items[0],
        )
        pod_name = pod.metadata.name
        logs = core.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=tail_lines)
        return pod_name, logs or ""

    def get_pod_detail(self, pod_name: str, namespace: str) -> dict:
        from datetime import datetime, timezone
        core = self._core()
        pod = core.read_namespaced_pod(pod_name, namespace)
        statuses = {cs.name: cs for cs in (pod.status.container_statuses or [])}
        containers = []
        for c in pod.spec.containers or []:
            cs = statuses.get(c.name)
            res = c.resources
            req = (res.requests or {}) if res else {}
            lim = (res.limits or {}) if res else {}
            containers.append({
                "name": c.name,
                "image": c.image or "",
                "ready": cs.ready if cs else False,
                "restart_count": cs.restart_count if cs else 0,
                "cpu_request": str(req["cpu"]) if "cpu" in req else None,
                "memory_request": str(req["memory"]) if "memory" in req else None,
                "cpu_limit": str(lim["cpu"]) if "cpu" in lim else None,
                "memory_limit": str(lim["memory"]) if "memory" in lim else None,
            })
        conditions = [
            {"type": c.type, "status": c.status, "reason": c.reason, "last_transition": c.last_transition_time}
            for c in (pod.status.conditions or [])
        ]
        evts = core.list_namespaced_event(
            namespace=namespace, field_selector=f"involvedObject.name={pod_name}"
        )
        events = []
        for e in evts.items:
            events.append({
                "reason": e.reason or "",
                "message": e.message or "",
                "type": e.type or "Normal",
                "count": e.count or 1,
                "last_time": e.last_timestamp or e.event_time,
            })
        events.sort(
            key=lambda x: x["last_time"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase or "Unknown",
            "node": pod.spec.node_name,
            "pod_ip": pod.status.pod_ip,
            "qos_class": pod.status.qos_class,
            "start_time": pod.status.start_time,
            "containers": containers,
            "conditions": conditions,
            "events": events[:20],
        }

    def restart_deployment(self, name: str, namespace: str) -> None:
        from datetime import datetime, timezone
        self._apps().patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"template": {"metadata": {"annotations": {
                "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat()
            }}}}},
        )

    def drain_node(self, node_name: str) -> int:
        from kubernetes.client import V1Eviction, V1ObjectMeta
        core = self._core()
        core.patch_node(node_name, {"spec": {"unschedulable": True}})
        pods = core.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
        evicted = 0
        for pod in pods.items:
            owners = pod.metadata.owner_references or []
            if any(o.kind == "DaemonSet" for o in owners) or not owners:
                continue
            try:
                core.create_namespaced_pod_eviction(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    body=V1Eviction(
                        metadata=V1ObjectMeta(
                            name=pod.metadata.name,
                            namespace=pod.metadata.namespace,
                        )
                    ),
                )
                evicted += 1
            except ApiException as e:
                if e.status == 404:
                    continue
                raise
        return evicted

    def cordon_node(self, node_name: str) -> None:
        self._core().patch_node(node_name, {"spec": {"unschedulable": True}})

    def uncordon_node(self, node_name: str) -> None:
        self._core().patch_node(node_name, {"spec": {"unschedulable": False}})

    def create_service(self, name: str, namespace: str, port: int) -> None:
        svc = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1ServiceSpec(
                selector={"app": name},
                ports=[client.V1ServicePort(port=port, target_port=port, protocol="TCP")],
                type="ClusterIP",
            ),
        )
        self._core().create_namespaced_service(namespace=namespace, body=svc)

    def delete_service(self, name: str, namespace: str) -> None:
        self._core().delete_namespaced_service(name=name, namespace=namespace)

    def create_ingress(self, name: str, namespace: str, host: str, port: int) -> None:
        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                annotations={
                    "traefik.ingress.kubernetes.io/router.entrypoints": "web,websecure",
                },
            ),
            spec=client.V1IngressSpec(
                ingress_class_name="traefik",
                tls=[client.V1IngressTLS(hosts=[host])],
                rules=[
                    client.V1IngressRule(
                        host=host,
                        http=client.V1HTTPIngressRuleValue(
                            paths=[
                                client.V1HTTPIngressPath(
                                    path="/",
                                    path_type="Prefix",
                                    backend=client.V1IngressBackend(
                                        service=client.V1IngressServiceBackend(
                                            name=name,
                                            port=client.V1ServiceBackendPort(number=port),
                                        )
                                    ),
                                )
                            ]
                        ),
                    )
                ],
            ),
        )
        self._networking().create_namespaced_ingress(namespace=namespace, body=ingress)

    def delete_ingress(self, name: str, namespace: str) -> None:
        self._networking().delete_namespaced_ingress(name=name, namespace=namespace)

    def get_rollout_history(self, name: str, namespace: str) -> list[dict]:
        apps = self._apps()
        deployment = apps.read_namespaced_deployment(name=name, namespace=namespace)
        current_revision = int(
            (deployment.metadata.annotations or {}).get("deployment.kubernetes.io/revision", "0")
        )
        rs_list = apps.list_namespaced_replica_set(
            namespace=namespace, label_selector=f"app={name}"
        )
        revisions = []
        for rs in rs_list.items:
            annotations = rs.metadata.annotations or {}
            rev_str = annotations.get("deployment.kubernetes.io/revision")
            if not rev_str:
                continue
            rev = int(rev_str)
            containers = (rs.spec.template.spec.containers or []) if rs.spec and rs.spec.template and rs.spec.template.spec else []
            image = containers[0].image if containers else "unknown"
            revisions.append({
                "revision": rev,
                "image": image,
                "created_at": rs.metadata.creation_timestamp,
                "is_current": rev == current_revision,
            })
        revisions.sort(key=lambda r: r["revision"], reverse=True)
        return revisions

    def get_cluster_events(
        self,
        namespace: str | None = None,
        event_type: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        core = self._core()
        events = (
            core.list_namespaced_event(namespace=namespace)
            if namespace
            else core.list_event_for_all_namespaces()
        )
        result = []
        for e in events.items:
            if event_type and e.type != event_type:
                continue
            result.append({
                "namespace": e.metadata.namespace or "default",
                "type": e.type or "Normal",
                "reason": e.reason or "",
                "message": e.message or "",
                "object_kind": (e.involved_object.kind if e.involved_object else "") or "",
                "object_name": (e.involved_object.name if e.involved_object else "") or "",
                "count": e.count or 1,
                "first_time": e.first_timestamp,
                "last_time": e.last_timestamp,
            })
        result.sort(
            key=lambda x: x["last_time"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return result[:limit]

    def list_namespaces(self) -> list[dict]:
        return [
            {
                "name": ns.metadata.name,
                "status": (ns.status.phase if ns.status else None) or "Unknown",
                "created_at": ns.metadata.creation_timestamp,
                "labels": {
                    k: v for k, v in (ns.metadata.labels or {}).items()
                    if not k.startswith("kubernetes.io/")
                },
            }
            for ns in self._core().list_namespace().items
        ]

    def create_namespace(self, name: str) -> None:
        self._core().create_namespace(
            body=client.V1Namespace(metadata=client.V1ObjectMeta(name=name))
        )

    def delete_namespace(self, name: str) -> None:
        self._core().delete_namespace(name=name)

    def _autoscaling(self) -> client.AutoscalingV2Api:
        return client.AutoscalingV2Api()

    def get_hpa(self, name: str, namespace: str) -> dict | None:
        try:
            hpa = self._autoscaling().read_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise
        spec = hpa.spec
        status = hpa.status
        cpu_target: int | None = None
        if spec.metrics:
            for m in spec.metrics:
                if m.type == "Resource" and m.resource and m.resource.name == "cpu":
                    if m.resource.target and m.resource.target.average_utilization is not None:
                        cpu_target = m.resource.target.average_utilization
                        break
        current_cpu: int | None = None
        if status and status.current_metrics:
            for m in status.current_metrics:
                if m.type == "Resource" and m.resource and m.resource.name == "cpu":
                    if m.resource.current and m.resource.current.average_utilization is not None:
                        current_cpu = m.resource.current.average_utilization
                        break
        return {
            "min_replicas": spec.min_replicas,
            "max_replicas": spec.max_replicas,
            "cpu_target_pct": cpu_target,
            "current_replicas": status.current_replicas if status else None,
            "current_cpu_pct": current_cpu,
        }

    def apply_hpa(self, name: str, namespace: str, min_replicas: int, max_replicas: int, cpu_target_pct: int) -> None:
        autoscaling = self._autoscaling()
        body = client.V2HorizontalPodAutoscaler(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V2HorizontalPodAutoscalerSpec(
                scale_target_ref=client.V2CrossVersionObjectReference(
                    api_version="apps/v1",
                    kind="Deployment",
                    name=name,
                ),
                min_replicas=min_replicas,
                max_replicas=max_replicas,
                metrics=[
                    client.V2MetricSpec(
                        type="Resource",
                        resource=client.V2ResourceMetricSource(
                            name="cpu",
                            target=client.V2MetricTarget(
                                type="Utilization",
                                average_utilization=cpu_target_pct,
                            ),
                        ),
                    )
                ],
            ),
        )
        try:
            autoscaling.read_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace)
            autoscaling.replace_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace, body=body)
        except ApiException as e:
            if e.status == 404:
                autoscaling.create_namespaced_horizontal_pod_autoscaler(namespace=namespace, body=body)
            else:
                raise

    def delete_hpa(self, name: str, namespace: str) -> None:
        try:
            self._autoscaling().delete_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise

    def list_configmaps(self, namespace: str = "pi-apps") -> list[dict]:
        cms = self._core().list_namespaced_config_map(namespace=namespace)
        result = []
        for cm in cms.items:
            name = cm.metadata.name or ""
            if name == "kube-root-ca.crt":
                continue
            result.append({
                "name": name,
                "namespace": cm.metadata.namespace or namespace,
                "data_keys": sorted((cm.data or {}).keys()),
                "created_at": cm.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: x["name"])
        return result

    def get_configmap(self, name: str, namespace: str) -> dict | None:
        try:
            cm = self._core().read_namespaced_config_map(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise
        return {
            "name": cm.metadata.name,
            "namespace": cm.metadata.namespace or namespace,
            "data": cm.data or {},
            "created_at": cm.metadata.creation_timestamp,
        }

    def create_configmap(self, name: str, namespace: str, data: dict[str, str]) -> None:
        self._core().create_namespaced_config_map(
            namespace=namespace,
            body=client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                data=data,
            ),
        )

    def update_configmap(self, name: str, namespace: str, data: dict[str, str]) -> None:
        self._core().replace_namespaced_config_map(
            name=name,
            namespace=namespace,
            body=client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                data=data,
            ),
        )

    def delete_configmap(self, name: str, namespace: str) -> None:
        try:
            self._core().delete_namespaced_config_map(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise

    def _networking(self) -> client.NetworkingV1Api:
        return client.NetworkingV1Api()

    def _batch(self) -> client.BatchV1Api:
        return client.BatchV1Api()

    # ── Secrets ──────────────────────────────────────────────────────────────

    _SECRET_SKIP = frozenset({"default-token", "kube-root-ca.crt"})

    def list_secrets(self, namespace: str = "pi-apps") -> list[dict]:
        result = []
        for s in self._core().list_namespaced_secret(namespace=namespace).items:
            name = s.metadata.name or ""
            if any(name.startswith(p) for p in ("default-token", "sh.helm")):
                continue
            result.append({
                "name": name,
                "namespace": s.metadata.namespace or namespace,
                "type": s.type or "Opaque",
                "data_keys": sorted((s.data or {}).keys()),
                "created_at": s.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: x["name"])
        return result

    def get_secret(self, name: str, namespace: str) -> dict | None:
        import base64
        try:
            s = self._core().read_namespaced_secret(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise
        data: dict[str, str] = {}
        for k, v in (s.data or {}).items():
            try:
                data[k] = base64.b64decode(v).decode("utf-8")
            except Exception:
                data[k] = "<binary>"
        return {
            "name": s.metadata.name,
            "namespace": s.metadata.namespace or namespace,
            "type": s.type or "Opaque",
            "data": data,
            "created_at": s.metadata.creation_timestamp,
        }

    def create_secret(self, name: str, namespace: str, data: dict[str, str], secret_type: str = "Opaque") -> None:
        import base64
        encoded = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}
        self._core().create_namespaced_secret(
            namespace=namespace,
            body=client.V1Secret(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                type=secret_type,
                data=encoded,
            ),
        )

    def update_secret(self, name: str, namespace: str, data: dict[str, str]) -> None:
        import base64
        encoded = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}
        self._core().replace_namespaced_secret(
            name=name,
            namespace=namespace,
            body=client.V1Secret(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                data=encoded,
            ),
        )

    def delete_secret(self, name: str, namespace: str) -> None:
        try:
            self._core().delete_namespaced_secret(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise

    # ── Services & Ingresses ─────────────────────────────────────────────────

    def list_services(self, namespace: str | None = None) -> list[dict]:
        core = self._core()
        items = (
            core.list_namespaced_service(namespace=namespace).items
            if namespace
            else core.list_service_for_all_namespaces().items
        )
        result = []
        for svc in items:
            ports = []
            for p in (svc.spec.ports or []):
                ports.append({
                    "port": p.port,
                    "target_port": str(p.target_port) if p.target_port else None,
                    "node_port": p.node_port,
                    "protocol": p.protocol or "TCP",
                })
            result.append({
                "name": svc.metadata.name,
                "namespace": svc.metadata.namespace,
                "type": (svc.spec.type or "ClusterIP"),
                "cluster_ip": svc.spec.cluster_ip,
                "external_ip": (svc.spec.external_i_ps or [None])[0],
                "ports": ports,
                "selector": svc.spec.selector or {},
                "created_at": svc.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    def list_ingresses(self, namespace: str | None = None) -> list[dict]:
        net = self._networking()
        items = (
            net.list_namespaced_ingress(namespace=namespace).items
            if namespace
            else net.list_ingress_for_all_namespaces().items
        )
        result = []
        for ing in items:
            rules = []
            for r in (ing.spec.rules or []):
                paths = []
                if r.http:
                    for p in (r.http.paths or []):
                        paths.append({
                            "path": p.path or "/",
                            "backend_service": (p.backend.service.name if p.backend and p.backend.service else None),
                            "backend_port": (p.backend.service.port.number if p.backend and p.backend.service and p.backend.service.port else None),
                        })
                rules.append({"host": r.host, "paths": paths})
            tls_hosts: list[str] = []
            for t in (ing.spec.tls or []):
                tls_hosts.extend(t.hosts or [])
            result.append({
                "name": ing.metadata.name,
                "namespace": ing.metadata.namespace,
                "rules": rules,
                "tls_hosts": tls_hosts,
                "ingress_class": (ing.spec.ingress_class_name or ing.metadata.annotations or {}).get("kubernetes.io/ingress.class") if isinstance((ing.spec.ingress_class_name or ing.metadata.annotations or {}).get("kubernetes.io/ingress.class"), str) else ing.spec.ingress_class_name,
                "created_at": ing.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    # ── CronJobs ─────────────────────────────────────────────────────────────

    def list_cronjobs(self, namespace: str | None = None) -> list[dict]:
        batch = self._batch()
        items = (
            batch.list_namespaced_cron_job(namespace=namespace).items
            if namespace
            else batch.list_cron_job_for_all_namespaces().items
        )
        result = []
        for cj in items:
            spec = cj.spec
            status = cj.status
            containers = []
            if spec and spec.job_template and spec.job_template.spec and spec.job_template.spec.template and spec.job_template.spec.template.spec:
                containers = spec.job_template.spec.template.spec.containers or []
            result.append({
                "name": cj.metadata.name,
                "namespace": cj.metadata.namespace,
                "schedule": spec.schedule if spec else "",
                "suspended": bool(spec.suspend) if spec else False,
                "active_jobs": len(status.active or []) if status else 0,
                "last_schedule_time": status.last_schedule_time if status else None,
                "image": containers[0].image if containers else "",
                "created_at": cj.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    def create_cronjob(self, name: str, namespace: str, schedule: str, image: str, command: list[str], env_vars: dict[str, str]) -> None:
        env = [client.V1EnvVar(name=k, value=v) for k, v in env_vars.items()]
        self._batch().create_namespaced_cron_job(
            namespace=namespace,
            body=client.V1CronJob(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=client.V1CronJobSpec(
                    schedule=schedule,
                    job_template=client.V1JobTemplateSpec(
                        spec=client.V1JobSpec(
                            template=client.V1PodTemplateSpec(
                                spec=client.V1PodSpec(
                                    restart_policy="OnFailure",
                                    containers=[
                                        client.V1Container(
                                            name=name,
                                            image=image,
                                            command=command if command else None,
                                            env=env if env else None,
                                        )
                                    ],
                                )
                            )
                        )
                    ),
                ),
            ),
        )

    def set_cronjob_suspend(self, name: str, namespace: str, suspend: bool) -> None:
        self._batch().patch_namespaced_cron_job(
            name=name,
            namespace=namespace,
            body={"spec": {"suspend": suspend}},
        )

    def delete_cronjob(self, name: str, namespace: str) -> None:
        try:
            self._batch().delete_namespaced_cron_job(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise

    def list_cronjob_jobs(self, name: str, namespace: str, limit: int = 10) -> list[dict]:
        jobs = self._batch().list_namespaced_job(
            namespace=namespace, label_selector=f"app={name}"
        )
        result = []
        for job in jobs.items:
            owner_refs = job.metadata.owner_references or []
            if not any(r.name == name for r in owner_refs):
                continue
            status = job.status
            result.append({
                "name": job.metadata.name,
                "succeeded": status.succeeded or 0,
                "failed": status.failed or 0,
                "active": status.active or 0,
                "start_time": status.start_time,
                "completion_time": status.completion_time,
            })
        result.sort(key=lambda x: x["start_time"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return result[:limit]

    def list_jobs(self, namespace: str | None = None) -> list[dict]:
        from datetime import datetime, timezone
        batch = self._batch()
        items = (
            batch.list_namespaced_job(namespace=namespace).items
            if namespace
            else batch.list_job_for_all_namespaces().items
        )
        result = []
        for job in items:
            st = job.status
            meta = job.metadata
            owner_refs = meta.owner_references or []
            cron_job = next((r.name for r in owner_refs if r.kind == "CronJob"), None)
            active = st.active or 0
            succeeded = st.succeeded or 0
            failed = st.failed or 0
            if active > 0:
                state = "running"
            elif failed > 0 and succeeded == 0:
                state = "failed"
            elif succeeded > 0:
                state = "succeeded"
            else:
                state = "unknown"
            result.append({
                "name": meta.name,
                "namespace": meta.namespace,
                "state": state,
                "active": active,
                "succeeded": succeeded,
                "failed": failed,
                "cron_job": cron_job,
                "start_time": st.start_time,
                "completion_time": st.completion_time,
                "created_at": meta.creation_timestamp,
            })
        result.sort(
            key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return result

    def list_resource_quotas(self, namespace: str | None = None) -> list[dict]:
        core = self._core()
        items = (
            core.list_namespaced_resource_quota(namespace=namespace).items
            if namespace
            else core.list_resource_quota_for_all_namespaces().items
        )
        result = []
        for rq in items:
            hard = (rq.status.hard or {}) if rq.status else {}
            used = (rq.status.used or {}) if rq.status else {}
            resources = sorted(
                [{"resource": r, "hard": str(v), "used": str(used.get(r, "0"))} for r, v in hard.items()],
                key=lambda x: x["resource"],
            )
            result.append({
                "name": rq.metadata.name,
                "namespace": rq.metadata.namespace,
                "resources": resources,
                "created_at": rq.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    def list_limit_ranges(self, namespace: str | None = None) -> list[dict]:
        core = self._core()
        items = (
            core.list_namespaced_limit_range(namespace=namespace).items
            if namespace
            else core.list_limit_range_for_all_namespaces().items
        )
        result = []
        for lr in items:
            limits = []
            for limit in (lr.spec.limits or []):
                limit_type = limit.type or "Container"
                all_res: set[str] = set()
                for d in [limit.max or {}, limit.min or {}, limit.default or {}, limit.default_request or {}]:
                    all_res.update(d.keys())
                for resource in sorted(all_res):
                    def _s(d: dict, k: str) -> str | None:
                        v = d.get(k)
                        return str(v) if v is not None else None
                    limits.append({
                        "type": limit_type,
                        "resource": resource,
                        "max": _s(limit.max or {}, resource),
                        "min": _s(limit.min or {}, resource),
                        "default": _s(limit.default or {}, resource),
                        "default_request": _s(limit.default_request or {}, resource),
                    })
            result.append({
                "name": lr.metadata.name,
                "namespace": lr.metadata.namespace,
                "limits": limits,
                "created_at": lr.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    # ── Storage ─────────────────────────────────────────────────────────────

    def list_pvcs(self, namespace: str | None = None) -> list[dict]:
        core = self._core()
        items = (
            core.list_namespaced_persistent_volume_claim(namespace=namespace).items
            if namespace
            else core.list_persistent_volume_claim_for_all_namespaces().items
        )
        result = []
        for pvc in items:
            spec = pvc.spec
            status = pvc.status
            capacity = (status.capacity or {}).get("storage") if status else None
            result.append({
                "name": pvc.metadata.name,
                "namespace": pvc.metadata.namespace,
                "status": (status.phase or "Unknown") if status else "Unknown",
                "capacity": capacity,
                "storage_class": spec.storage_class_name if spec else None,
                "access_modes": (spec.access_modes or []) if spec else [],
                "volume_name": spec.volume_name if spec else None,
                "created_at": pvc.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    def delete_pvc(self, name: str, namespace: str) -> None:
        try:
            self._core().delete_namespaced_persistent_volume_claim(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise

    def list_pvs(self) -> list[dict]:
        result = []
        for pv in self._core().list_persistent_volume().items:
            spec = pv.spec
            status = pv.status
            claim_ref = spec.claim_ref if spec else None
            capacity = (spec.capacity or {}).get("storage") if spec else None
            result.append({
                "name": pv.metadata.name,
                "status": (status.phase or "Unknown") if status else "Unknown",
                "capacity": capacity,
                "access_modes": (spec.access_modes or []) if spec else [],
                "storage_class": spec.storage_class_name if spec else None,
                "reclaim_policy": spec.persistent_volume_reclaim_policy if spec else None,
                "claim_namespace": claim_ref.namespace if claim_ref else None,
                "claim_name": claim_ref.name if claim_ref else None,
                "created_at": pv.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: x["name"])
        return result

    # ── Pod helpers ──────────────────────────────────────────────────────────

    def list_pods_in_namespace(self, namespace: str) -> list[dict]:
        pods = self._core().list_namespaced_pod(namespace)
        result = []
        for p in pods.items:
            containers = [c.name for c in (p.spec.containers or [])]
            result.append({
                "name": p.metadata.name,
                "phase": p.status.phase or "Unknown",
                "containers": containers,
            })
        result.sort(key=lambda x: x["name"])
        return result

    def get_first_pod_name(self, name: str, namespace: str) -> str | None:
        pods = self._core().list_namespaced_pod(
            namespace=namespace, label_selector=f"app={name}"
        )
        running = [p for p in pods.items if p.status and p.status.phase == "Running"]
        pod = running[0] if running else (pods.items[0] if pods.items else None)
        return pod.metadata.name if pod else None

    def list_storage_classes(self) -> list[dict]:
        result = []
        for sc in self._storage().list_storage_class().items:
            annotations = sc.metadata.annotations or {}
            is_default = annotations.get(
                "storageclass.kubernetes.io/is-default-class", ""
            ) == "true"
            result.append({
                "name": sc.metadata.name,
                "provisioner": sc.provisioner or "",
                "reclaim_policy": sc.reclaim_policy or "Delete",
                "binding_mode": sc.volume_binding_mode or "Immediate",
                "is_default": is_default,
                "created_at": sc.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (not x["is_default"], x["name"]))
        return result

    def create_pvc(
        self,
        name: str,
        namespace: str,
        storage_class: str,
        access_modes: list[str],
        size: str,
    ) -> None:
        self._core().create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=client.V1PersistentVolumeClaimSpec(
                    storage_class_name=storage_class,
                    access_modes=access_modes,
                    resources=client.V1ResourceRequirements(
                        requests={"storage": size}
                    ),
                ),
            ),
        )

    # ── StatefulSets & DaemonSets ────────────────────────────────────────────

    def list_statefulsets(self, namespace: str | None = None) -> list[dict]:
        apps = self._apps()
        items = (
            apps.list_namespaced_stateful_set(namespace=namespace).items
            if namespace
            else apps.list_stateful_set_for_all_namespaces().items
        )
        result = []
        for sts in items:
            spec = sts.spec
            status = sts.status
            containers = []
            if spec and spec.template and spec.template.spec:
                containers = spec.template.spec.containers or []
            result.append({
                "name": sts.metadata.name,
                "namespace": sts.metadata.namespace,
                "replicas": spec.replicas if spec else 0,
                "ready_replicas": (status.ready_replicas or 0) if status else 0,
                "service_name": spec.service_name if spec else None,
                "images": [c.image for c in containers if c.image],
                "created_at": sts.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    def list_daemonsets(self, namespace: str | None = None) -> list[dict]:
        apps = self._apps()
        items = (
            apps.list_namespaced_daemon_set(namespace=namespace).items
            if namespace
            else apps.list_daemon_set_for_all_namespaces().items
        )
        result = []
        for ds in items:
            spec = ds.spec
            status = ds.status
            containers = []
            if spec and spec.template and spec.template.spec:
                containers = spec.template.spec.containers or []
            result.append({
                "name": ds.metadata.name,
                "namespace": ds.metadata.namespace,
                "desired": (status.desired_number_scheduled or 0) if status else 0,
                "current": (status.current_number_scheduled or 0) if status else 0,
                "ready": (status.number_ready or 0) if status else 0,
                "available": (status.number_available or 0) if status else 0,
                "images": [c.image for c in containers if c.image],
                "created_at": ds.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    # ── Helm releases ────────────────────────────────────────────────────────

    def list_helm_releases(self, namespace: str | None = None) -> list[dict]:
        import base64
        import gzip
        import json as _json

        core = self._core()
        try:
            items = (
                core.list_namespaced_secret(
                    namespace=namespace, label_selector="owner=helm"
                ).items
                if namespace
                else core.list_secret_for_all_namespaces(
                    label_selector="owner=helm"
                ).items
            )
        except ApiException:
            return []

        latest: dict[tuple[str, str], dict] = {}
        for secret in items:
            labels = secret.metadata.labels or {}
            raw = (secret.data or {}).get("release")
            if not raw:
                continue
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("ascii")
                decoded = base64.b64decode(raw)
                try:
                    decompressed = gzip.decompress(decoded)
                except Exception:
                    decompressed = gzip.decompress(base64.b64decode(decoded))
                release = _json.loads(decompressed)
            except Exception:
                continue

            rel_name = release.get("name") or secret.metadata.name
            rel_ns = release.get("namespace") or secret.metadata.namespace or ""
            key = (rel_ns, rel_name)
            version = release.get("version", 0)

            if key not in latest or latest[key]["revision"] < version:
                chart_meta = (release.get("chart") or {}).get("metadata") or {}
                info = release.get("info") or {}
                latest[key] = {
                    "name": rel_name,
                    "namespace": rel_ns,
                    "chart": chart_meta.get("name", "unknown"),
                    "chart_version": chart_meta.get("version"),
                    "app_version": chart_meta.get("appVersion"),
                    "status": info.get("status") or labels.get("status", "unknown"),
                    "revision": version,
                    "description": info.get("description"),
                    "first_deployed": info.get("first_deployed"),
                    "last_deployed": info.get("last_deployed"),
                }

        result = list(latest.values())
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    # ── RBAC ─────────────────────────────────────────────────────────────────

    def _rbac(self) -> client.RbacAuthorizationV1Api:
        return client.RbacAuthorizationV1Api(_load_api())

    def list_cluster_roles(self, hide_system: bool = True) -> list[dict]:
        result = []
        for cr in self._rbac().list_cluster_role().items:
            name = cr.metadata.name or ""
            if hide_system and name.startswith("system:"):
                continue
            rules = [
                {
                    "api_groups": rule.api_groups or [],
                    "resources": rule.resources or [],
                    "verbs": rule.verbs or [],
                }
                for rule in (cr.rules or [])
            ]
            result.append({
                "name": name,
                "rules_count": len(rules),
                "rules": rules,
                "created_at": cr.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: x["name"])
        return result

    def list_cluster_role_bindings(self, hide_system: bool = True) -> list[dict]:
        result = []
        for crb in self._rbac().list_cluster_role_binding().items:
            name = crb.metadata.name or ""
            if hide_system and name.startswith("system:"):
                continue
            subjects = [
                {"kind": s.kind, "name": s.name, "namespace": s.namespace}
                for s in (crb.subjects or [])
            ]
            result.append({
                "name": name,
                "role_kind": crb.role_ref.kind if crb.role_ref else None,
                "role_name": crb.role_ref.name if crb.role_ref else None,
                "subjects": subjects,
                "created_at": crb.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: x["name"])
        return result

    def list_service_accounts(self, namespace: str | None = None) -> list[dict]:
        core = self._core()
        items = (
            core.list_namespaced_service_account(namespace=namespace).items
            if namespace
            else core.list_service_account_for_all_namespaces().items
        )
        result = []
        for sa in items:
            name = sa.metadata.name or ""
            if name == "default":
                continue
            result.append({
                "name": name,
                "namespace": sa.metadata.namespace,
                "secrets_count": len(sa.secrets or []),
                "created_at": sa.metadata.creation_timestamp,
            })
        result.sort(key=lambda x: (x["namespace"], x["name"]))
        return result

    def rollback_deployment(self, name: str, namespace: str, revision: int) -> str:
        apps = self._apps()
        rs_list = apps.list_namespaced_replica_set(
            namespace=namespace, label_selector=f"app={name}"
        )
        target_rs = None
        for rs in rs_list.items:
            annotations = rs.metadata.annotations or {}
            if annotations.get("deployment.kubernetes.io/revision") == str(revision):
                target_rs = rs
                break
        if target_rs is None:
            raise ValueError(f"Revision {revision} not found for workload {name}")
        containers = (target_rs.spec.template.spec.containers or []) if target_rs.spec and target_rs.spec.template and target_rs.spec.template.spec else []
        target_image = containers[0].image if containers else None
        template_dict = client.ApiClient().sanitize_for_serialization(target_rs.spec.template)
        apps.patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"template": template_dict}},
        )
        return target_image or "unknown"
