# SigNoz + Grafana Observability Assignment

**(FastAPI + OpenTelemetry)**

## Overview

This repository contains:

* A FastAPI app instrumented with OpenTelemetry (traces, metrics, logs)
* A local SigNoz stack (Docker Compose)
* A local Grafana OTEL stack (Grafana + Tempo + Loki + Prometheus + OTel Collector + Alloy)

---

## Project Structure

```
app/                   # FastAPI app + environment files
signoz/                # SigNoz Docker setup
grafana-otel-stack/    # Grafana OTEL stack setup
requirements.txt       # Python dependencies
```

---

## Prerequisites

* Python 3.9+
* Docker
* Docker Compose

---

# 1️⃣ Run SigNoz Stack

```bash
cd signoz
docker compose up -d
docker compose ps
```

Open SigNoz:

```
http://localhost:8080
```

---

## Run FastAPI App → Send data to SigNoz

Open a new terminal:

```bash
cd app
source .env.signoz
uvicorn main:app --reload
```

Generate traffic:

```bash
curl http://127.0.0.1:8000/fast
curl http://127.0.0.1:8000/slow
curl http://127.0.0.1:8000/error
```

Verify in SigNoz:

* Services → `signoz-fastapi-demo`
* Traces
* Logs
* Metrics

---

# 2️⃣ Run Grafana OTEL Stack

```bash
cd grafana-otel-stack
docker compose up -d
docker compose ps
```

Open Grafana:

```
http://localhost:3000
```

Login:

```
admin / admin
```

---

## Run FastAPI App → Send data to Grafana Stack

Stop previous `uvicorn` if running.

```bash
cd app
source .env.grafana
uvicorn main:app --reload
```

Generate traffic again:

```bash
curl http://127.0.0.1:8000/fast
curl http://127.0.0.1:8000/slow
curl http://127.0.0.1:8000/error
```

Verify in Grafana:

* Tempo → Traces
* Loki → Logs
* Prometheus → Metrics
* Explore → Query logs and traces

---

## Custom Metrics Implemented

* `demo_request_count` (Counter)
* `demo_request_latency_ms` (Histogram)
* `demo_live_users` (Observable Gauge)

---

## Switching Backends

To send data to SigNoz:

```bash
source .env.signoz
```

To send data to Grafana stack:

```bash
source .env.grafana
```

No code changes required.
