import pytest
from unittest.mock import patch

MOCK_PODS = [{"name": "app-abc-123", "phase": "Running", "containers": ["app"]}]


@pytest.mark.asyncio
async def test_list_pods(client, auth_headers):
    with patch("app.api.v1.pods.K8sService") as MockK8s:
        MockK8s.return_value.list_pods_in_namespace.return_value = MOCK_PODS
        r = await client.get("/api/v1/pods/?namespace=pi-apps", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_pod_detail(client, auth_headers):
    mock_detail = {
        "name": "app-abc-123", "namespace": "pi-apps", "phase": "Running",
        "node": "pi-node1", "pod_ip": "10.42.0.1", "qos_class": "BestEffort",
        "start_time": "2024-01-01T00:00:00", "containers": [], "conditions": [], "events": [],
    }
    with patch("app.api.v1.pods.K8sService") as MockK8s:
        MockK8s.return_value.get_pod_detail.return_value = mock_detail
        r = await client.get("/api/v1/pods/pi-apps/app-abc-123", headers=auth_headers)
        assert r.status_code == 200
