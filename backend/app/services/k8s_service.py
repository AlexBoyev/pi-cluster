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
