# Pi-Cluster Architecture

## 1. Overview

Pi-Cluster is a DevOps control platform for monitoring and eventually orchestrating a Raspberry Pi cluster.

The architecture separates:

* Web UI
* API
* business logic
* persistent data
* cache and distributed coordination
* monitoring
* infrastructure access
* orchestration

The system should remain modular so individual components can evolve without requiring a complete rewrite.

---

# 2. High-Level Architecture

```text
                    ┌─────────────────────┐
                    │   React Dashboard   │
                    │   TypeScript / Vite │
                    └──────────┬──────────┘
                               │
                               │ HTTP / REST
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │ PostgreSQL  │  │    Redis    │  │ Monitoring  │
       │ Persistent  │  │ Cache/Locks │  │   Service   │
       │ State       │  │             │  │             │
       └─────────────┘  └─────────────┘  └──────┬──────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │ Prometheus  │
                                         └──────┬──────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │   Grafana   │
                                         └─────────────┘

                         Infrastructure
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
          Pi Node 1        Pi Node 2        Pi Node N
```

---

# 3. Frontend

Technology:

* React
* TypeScript
* Vite

The frontend is responsible for:

* dashboard presentation
* navigation
* cluster visualization
* node information
* monitoring charts
* deployment management in the future
* orchestration management in the future

The frontend must not:

* contain SSH credentials
* communicate directly with Raspberry Pis
* contain infrastructure secrets
* implement backend business logic

All infrastructure operations go through the backend API.

---

# 4. Backend

Technology:

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic

The backend is the control plane of Pi-Cluster.

Responsibilities:

* REST API
* authentication
* authorization
* cluster inventory
* node management
* SSH operations
* monitoring integration
* orchestration
* deployment management
* audit logging

Architecture:

```text
API Routes
    ↓
Services
    ↓
Repositories
    ↓
PostgreSQL
```

Infrastructure operations are accessed through dedicated services rather than directly from API routes.

---

# 5. PostgreSQL

PostgreSQL is the persistent source of truth.

Store:

* users
* roles
* clusters
* nodes
* network devices
* deployments
* configuration
* audit logs

Do not use PostgreSQL as the primary high-frequency time-series metrics database.

---

# 6. Redis

Redis provides fast ephemeral and coordination functionality.

Use Redis for:

* caching
* sessions
* rate limiting
* distributed locks
* orchestration locks
* background task coordination
* temporary state

Redis must not replace PostgreSQL as the persistent source of truth.

Example future lock:

```text
node:{node_id}:lock
```

This prevents conflicting operations against the same node.

---

# 7. Monitoring

Initial monitoring:

```text
Raspberry Pi
     ↓
SSH Metrics Collector
     ↓
Backend Monitoring Service
     ↓
Prometheus
     ↓
Grafana
```

Future monitoring:

```text
Raspberry Pi
     ↓
Node Exporter
     ↓
Prometheus
     ↓
Grafana
```

The application should use a monitoring abstraction so the metrics provider can change without rewriting the dashboard.

---

# 8. SSH

SSH is initially used for:

* health checks
* CPU information
* memory information
* disk information
* uptime
* temperature
* system information

The backend owns SSH credentials.

The frontend must never receive SSH credentials.

Arbitrary shell execution must not be exposed through the API.

Commands should be explicitly defined and controlled by the backend.

---

# 9. Current Infrastructure

## Network

```text
10.100.102.0/24
```

Router:

```text
10.100.102.1
```

Cluster switch:

```text
10.100.102.200
```

## Nodes

```text
pi-node1 → 10.100.102.10
pi-node2 → 10.100.102.5
pi-node3 → 10.100.102.17
pi-node4 → 10.100.102.12
```

The infrastructure inventory should eventually be represented through configuration and database records rather than hardcoded into frontend code.

---

# 10. Node State

Use a common node status model:

```text
ONLINE
OFFLINE
DEGRADED
UNKNOWN
```

All services should use the same state definitions.

A failure of one node must not cause the entire dashboard or API to fail.

---

# 11. Future Orchestration

The future orchestration layer will manage:

* workloads
* deployments
* services
* scheduling
* node capacity
* health checks
* load balancing

Conceptual architecture:

```text
API
 ↓
Orchestration Engine
 ↓
Scheduler
 ↓
Capacity Check
 ↓
Distributed Lock
 ↓
Selected Node
 ↓
Deployment Engine
 ↓
Container Runtime
```

The initial implementation should not attempt to recreate Kubernetes.

Start with simple, explicit orchestration primitives.

---

# 12. Future Load Balancing

Potential technologies:

* Traefik
* Nginx
* HAProxy

The final technology should be selected based on the actual deployment requirements.

Do not tightly couple the orchestration layer to one load-balancer implementation.

---

# 13. Security

Secrets belong in environment configuration or a proper secrets manager.

Never:

* commit passwords
* log passwords
* log access tokens
* expose SSH credentials
* place credentials in frontend code
* expose unrestricted shell execution

Production deployments should eventually use SSH keys rather than password authentication.

---

# 14. Design Principles

Pi-Cluster should follow:

* separation of concerns
* dependency injection
* explicit interfaces
* typed APIs
* modular services
* testability
* reproducible infrastructure
* minimal coupling
* incremental development

Avoid premature abstraction.

Do not build future features before they are required.
