#!/usr/bin/env python3
"""Seed the cluster node inventory into the database via the API."""
import sys
import httpx

API = "http://10.100.102.10:8000/api/v1"

NODES = [
    {"name": "pi-node1", "ip_address": "10.100.102.10"},
    {"name": "pi-node2", "ip_address": "10.100.102.5"},
    {"name": "pi-node3", "ip_address": "10.100.102.17"},
    {"name": "pi-node4", "ip_address": "10.100.102.12"},
]

errors = 0
for node in NODES:
    try:
        r = httpx.post(f"{API}/nodes/", json=node, timeout=10)
        if r.status_code == 201:
            print(f"  created  : {node['name']} ({node['ip_address']})")
        elif r.status_code == 409:
            print(f"  exists   : {node['name']}")
        else:
            print(f"  error {r.status_code}: {node['name']} — {r.text}")
            errors += 1
    except Exception as exc:
        print(f"  failed   : {node['name']} — {exc}")
        errors += 1

sys.exit(errors)
