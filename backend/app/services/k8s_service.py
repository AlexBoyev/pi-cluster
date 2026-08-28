import logging
import re
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
    ) -> None:
        node_selector = {"kubernetes.io/hostname": target_node} if target_node else None
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
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": cpu_request, "memory": memory_request}
                                ),
                            )
                        ],
                    ),
                ),
            ),
        )
        self._apps().create_namespaced_deployment(namespace=namespace, body=deployment)

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
