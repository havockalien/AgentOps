# 🤖 AgentOps — Enterprise AI Orchestration Operating System

[![CI Pipeline](https://github.com/madebyayush/AgentOps/actions/workflows/ci.yml/badge.svg)](https://github.com/madebyayush/AgentOps/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![Database](https://img.shields.io/badge/PostgreSql-4169e1?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Cache](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis)](https://redis.io)
[![Licensed](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

AgentOps is an autonomous, enterprise-grade operating system designed to manage and orchestrate resilient multi-agent cognitive networks. It establishes a robust, secure foundation capable of routing workflow traffic, executing tool invocations dynamically via MCP adapters, managing complex episodic and long-term vector memories, enforcing granular role-based clearances (RBAC), and detecting real-time operational failures.

---

## 🗺️ Architectural Monorepo Blueprint

```text
AgentOps/
├── apps/
│   ├── ui/                  # React + Vite + TS Frontend Dashboard (Glassmorphism design)
│   ├── api-gateway/         # FastAPI Main Gateway entrypoint (Auth, middleware, & routes)
│   └── agent-runtime/       # Asynchronous Python cognitive engine & Kafka execution loop
├── packages/
│   ├── shared-types/        # Pydantic + TypeScript shared schemas & data contracts
│   ├── memory/              # Memory subsystems adapters (Qdrant, Pinecone, Redis)
│   ├── tools/               # Registered actions registry and MCP adapters
│   ├── observability/       # OpenTelemetry traces SDK configurations (Jaeger, Prometheus)
│   └── security/            # Auth, RBAC clearances, and dynamic PII redaction middleware
├── infra/
│   ├── docker/              # Multi-stage production Dockerfiles per service
│   ├── k8s/                 # Kubernetes Deployment, Service, and HPA descriptors
│   └── terraform/           # IaC VPC network, RDS database, and ElastiCache modules
├── scripts/                 # PowerShell and shell environment bootstrapping utilities
├── tests/                   # Monorepo E2E integration and flow tests
├── .env.example             # Exhaustive templates for third-party keys & database URIs
├── docker-compose.yml       # Local development stack (Postgres, Redis, Kafka, Qdrant, etc.)
└── README.md
```

---

## 🚀 Phase 1 Backend Completion

Core Backend and Database structures are fully implemented, optimized, and validated:

### 1. Robust Relational Schema (PostgreSQL via SQLAlchemy 2.0 Async)
- **`Agent`**: registered models configuration and model hyper-parameters.
- **`Run`**: tracking execution pipelines (queued → running → completed/failed).
- **`MemoryEntry`**: managing namespace-isolated short/long term semantic inputs.
- **`Tool`**: dynamically configured tools, parameters schemas, and MCP bindings.
- **`Workflow`**: DAG node-edge configurations and state versions tracking.
- **`HitlRequest`**: Human-in-the-loop pending approval gates (blocking run decisions).
- **`AuditLog`**: immutable, sequential security tracking for operational actions.
- **`Incident`**: anomalies, SLA breaches, and failure remediation records.

### 2. High-Performance Middleware Stack
- **`Auth Gate`**: Dual-layer verification supporting high-security JWT validation (via `jose`) alongside fallback hashed API-key header validation.
- **`Sliding Window Rate Limiter`**: Fast, Redis Sorted Sets-driven rate limit tracker executing per-user, per-endpoint buckets.
- **`PII Redactor`**: Middleware scanning outgoing JSON responses for emails, phone numbers, SSNs, credit cards, and API-keys, sanitizing log files automatically.

---

## 🧠 Phase 2 Asynchronous Cognitive Runtime Engine (LangGraph Engine)

The core asynchronous cognitive agent execution loop has been fully built, optimized, and tested:

### 1. State-Driven Orchestration (LangGraph & StateGraph)
- **`AgentState` TypedDict**: Manages thread-safe execution variables (including memory context, plans, current execution step, tool call history, and human-in-the-loop pending approval flags).
- **Core Abstractions (`BaseAgent`)**: Standardized Agent interface with `think` (planning), `act` (execution), and `reflect` (evaluation) steps, implementing the standard ReAct loop.
- **Asynchronous Execution Loop (`AgentRuntimeEngine`)**: Handles ingestion of runs from the Redis queue, schedules cognitive execution workflows concurrently, and coordinates pub/sub telemetry notifications.

### 2. Multi-Agent & Tool Sandbox Execution Layers
- **Sandboxed Tool Runners**: Secure execution environments with safe limits:
  - `CodeRunnerTool`: Subprocess-based Python sandboxing with CPU/RAM execution limits and 10-second timeouts.
  - `FileReaderTool`: Path-traversal blocked reader/writer restricted to workspace bounds.
  - `WebSearchTool`: Dynamic web search queries via SerpAPI adapters.
  - `SqlRunnerTool`: Read-only Postgres queries with explicit DML/DDL blocklists.
- **Hierarchical Cognitive Teams**: Structures orchestrators, specialist agents, and micro-workers into multi-agent crews (`ResearchCrew`, `DevOpsCrew`, `FullStackCrew`) with automated multi-perspective debate logic.

### 3. Fault Tolerance & Memory Systems
- **Two-Tier Memory Client**: Integrates instant episodic retrieval (via Redis) with semantic search (stubbed in dev; Pinecone ready).
- **Self-Correction & Gated Approvals**: Implements validation against schemas and logical verification. Failsafe routes trigger automatic retries (up to 3 times) before escalating to Human-in-the-loop (HITL) checkpoints.

---

## 🛠️ Developer Velocity & Testing Engine

To maintain high development speed, I've introduced dedicated developer testing tools under `apps/api-gateway`:

### 1. Boilerplate Mocks Library (`tests/boilerplate_mocks.py`)
Ready-to-use, typed, in-memory mocks representing key enterprise backbones:
- `MockAsyncSession`: SQLAlchemy async session mock.
- `MockRedisClient`: In-memory async Redis cache & pub/sub broker.
- `MockLLMClient`: Modern OpenAI `AsyncOpenAI` client completion stub (`chat.completions.create`) returning compliant completions without API keys.
- `MockKafkaBroker`: Mock event bus tracking message dispatches.

### 2. Automated AST Pytest Scaffolder CLI (`scripts/generate_pytest.py`)
Reads any FastAPI router and instantly scaffolds a robust pytest suite:
```bash
python scripts/generate_pytest.py --router apps/api-gateway/app/routers/tools.py
```
This auto-generates `test_generated_tools.py` under the `tests/` folder checking success states (200/201), authentication gates (401), and Pydantic validation failures (422).

---

## 🧪 Running the Test Suite

Pipeline runs completely isolated from live PostgreSQL/Redis backends by leveraging **in-memory SQLite (`aiosqlite`)** and **`fakeredis`** context pools, executing all tests in under 4 seconds.

### Quick Start (Local Verification)
1. Navigate to the API gateway:
   ```bash
   cd apps/api-gateway
   ```
2. Install test dependencies:
   ```bash
   pip install -r pyproject.toml
   ```
3. Run the comprehensive test suite (147 test cases):
   ```bash
   python -m pytest tests/ -v
   ```

---

## 🌐 Local Dev Infrastructure Setup

1. Boot the developer dependencies cluster:
   ```bash
   docker compose up -d
   ```
2. Setup and watch monorepo services:
   ```bash
   npm run dev
   ```

*Services Map:* PostgreSQL (`5432`), Redis (`6379`), Kafka (`9092`), Qdrant (`6333`), Jaeger (`16686`), MinIO (`9000`), Grafana (`3000`).
