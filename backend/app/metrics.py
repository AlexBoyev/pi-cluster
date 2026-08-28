from prometheus_client import Gauge

node_online = Gauge(
    "pi_cluster_node_online",
    "1 if node is ONLINE, 0 otherwise",
    ["node_name", "ip_address"],
)
node_cpu_load = Gauge(
    "pi_cluster_node_cpu_load_1m",
    "1-minute load average",
    ["node_name", "ip_address"],
)
node_memory_percent = Gauge(
    "pi_cluster_node_memory_percent",
    "Memory usage percent",
    ["node_name", "ip_address"],
)
node_disk_percent = Gauge(
    "pi_cluster_node_disk_percent",
    "Disk usage percent",
    ["node_name", "ip_address"],
)
node_temperature = Gauge(
    "pi_cluster_node_temperature_celsius",
    "CPU temperature in Celsius",
    ["node_name", "ip_address"],
)
node_uptime = Gauge(
    "pi_cluster_node_uptime_seconds",
    "Node uptime in seconds",
    ["node_name", "ip_address"],
)
