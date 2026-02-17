from fastapi import FastAPI
from fastapi.responses import JSONResponse
import time
import os
import random
import logging

# ---------- OpenTelemetry: Traces ----------
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ---------- OpenTelemetry: Metrics ----------
from opentelemetry import metrics
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

# ---------- OpenTelemetry: Logs ----------
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging import LoggingInstrumentor


# -----------------------------
# Config 
# -----------------------------
# Expected examples:
#   SigNoz:  http://localhost:4318
#   Grafana: http://localhost:14318  

OTLP_BASE = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if not OTLP_BASE:
    raise RuntimeError(
        "OTEL_EXPORTER_OTLP_ENDPOINT is not set. "
        "Load .env.signoz or .env.grafana before running uvicorn."
    )

# 1) SigNoz/Grafana will show this as the "Service"
resource = Resource.create({"service.name": "signoz-fastapi-demo"})

# ---------- TRACES ----------
trace.set_tracer_provider(TracerProvider(resource=resource))
trace_exporter = OTLPSpanExporter(endpoint=f"{OTLP_BASE}/v1/traces")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(trace_exporter))

# ---------- METRICS ----------
metric_exporter = OTLPMetricExporter(endpoint=f"{OTLP_BASE}/v1/metrics")
metric_reader = PeriodicExportingMetricReader(metric_exporter)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

# ---------- LOGS ----------
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)

log_exporter = OTLPLogExporter(endpoint=f"{OTLP_BASE}/v1/logs")
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

# Hook Python logging into OpenTelemetry logging
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.basicConfig(level=logging.INFO, handlers=[handler])

# Add trace_id/span_id to log format automatically
LoggingInstrumentor().instrument(set_logging_format=True)
logger = logging.getLogger("app")

logger.info(f"OTEL exporter base endpoint set to: {OTLP_BASE}")

# ---------- FastAPI app ----------
app = FastAPI()

# ---------- Custom Metrics ----------
meter = metrics.get_meter("signoz.fastapi.demo")

request_count = meter.create_counter("demo_request_count")
request_latency = meter.create_histogram("demo_request_latency_ms")

def live_users_cb(_):
    yield Observation(random.randint(10, 50))

meter.create_observable_gauge("demo_live_users", callbacks=[live_users_cb])

# ---------- Auto-instrument FastAPI ----------
FastAPIInstrumentor.instrument_app(
    app,
    tracer_provider=trace.get_tracer_provider(),
    meter_provider=metrics.get_meter_provider(),
)

# ---------- Routes ----------
@app.get("/")
def home():
    return {"message": "App is running"}

@app.get("/fast")
def fast():
    start = time.time()

    logger.info("fast endpoint hit")
    request_count.add(1, {"endpoint": "fast"})

    request_latency.record((time.time() - start) * 1000, {"endpoint": "fast"})
    return {"ok": True, "endpoint": "fast"}

@app.get("/slow")
def slow():
    start = time.time()

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("simulate_work") as span:
        logger.info("slow endpoint hit")
        logger.info(f"current span trace_id: {span.get_span_context().trace_id}")
        time.sleep(2)

    request_count.add(1, {"endpoint": "slow"})
    request_latency.record((time.time() - start) * 1000, {"endpoint": "slow"})
    return {"ok": True, "endpoint": "slow"}

@app.get("/error")
def error():
    start = time.time()

    logger.error("error endpoint hit")
    request_count.add(1, {"endpoint": "error"})
    request_latency.record((time.time() - start) * 1000, {"endpoint": "error"})
    return JSONResponse(status_code=500, content={"ok": False, "endpoint": "error"})
