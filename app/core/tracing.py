"""
OpenTelemetry distributed tracing setup for Queue Management System.

Instruments:
  - FastAPI HTTP requests
  - SQLAlchemy database queries
  - Redis cache operations
  - Celery task execution

Exports to:
  - Jaeger (via OTLP gRPC) in production
  - Console (stdout) when OTEL_EXPORTER=console
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def setup_tracing(app=None, service_name: str = "queue-management-api") -> Optional[object]:
    """
    Configure and start OpenTelemetry tracing.

    Returns the configured TracerProvider, or None if tracing is disabled.

    Environment variables:
        OTEL_ENABLED         = true | false  (default: false)
        OTEL_EXPORTER        = otlp | console (default: otlp)
        OTEL_ENDPOINT        = http://jaeger:4317  (gRPC OTLP)
        OTEL_SERVICE_NAME    = override service name
        OTEL_SAMPLE_RATE     = 0.0–1.0 (default: 1.0)
    """
    enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("OpenTelemetry tracing disabled (set OTEL_ENABLED=true to enable)")
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        service = os.getenv("OTEL_SERVICE_NAME", service_name)
        version = os.getenv("APP_VERSION", "1.0.0")
        environment = os.getenv("APP_ENV", "development")
        sample_rate = float(os.getenv("OTEL_SAMPLE_RATE", "1.0"))
        exporter_type = os.getenv("OTEL_EXPORTER", "otlp")

        resource = Resource.create({
            SERVICE_NAME: service,
            SERVICE_VERSION: version,
            "deployment.environment": environment,
        })

        sampler = ParentBased(root=TraceIdRatioBased(sample_rate))
        provider = TracerProvider(resource=resource, sampler=sampler)

        # ── Exporter ───────────────────────────────────────────────────────────
        if exporter_type == "console":
            exporter = ConsoleSpanExporter()
            logger.info("OpenTelemetry: using Console exporter")
        else:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            endpoint = os.getenv("OTEL_ENDPOINT", "http://jaeger-collector:4317")
            exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            logger.info(f"OpenTelemetry: using OTLP exporter → {endpoint}")

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # ── Auto-instrument libraries ──────────────────────────────────────────
        _instrument_fastapi(app)
        _instrument_sqlalchemy()
        _instrument_redis()
        _instrument_celery()

        logger.info(
            f"✅ OpenTelemetry tracing enabled — service={service}, "
            f"sample_rate={sample_rate}, exporter={exporter_type}"
        )
        return provider

    except ImportError as e:
        logger.warning(
            f"OpenTelemetry packages not installed, tracing disabled. "
            f"Install: pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc "
            f"opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-sqlalchemy "
            f"opentelemetry-instrumentation-redis opentelemetry-instrumentation-celery\n"
            f"Missing: {e}"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
        return None


def _instrument_fastapi(app):
    """Instrument FastAPI to create spans for HTTP requests."""
    if app is None:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,metrics",  # Don't trace health/metrics endpoints
            server_request_hook=_request_hook,
        )
        logger.debug("OpenTelemetry: FastAPI instrumented")
    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed, skipping")


def _request_hook(span, scope):
    """Add custom attributes to HTTP request spans."""
    if span and span.is_recording():
        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode("utf-8", errors="ignore")
        if request_id:
            span.set_attribute("http.request_id", request_id)


def _instrument_sqlalchemy():
    """Instrument SQLAlchemy to create spans for DB queries."""
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
        logger.debug("OpenTelemetry: SQLAlchemy instrumented")
    except ImportError:
        logger.warning("opentelemetry-instrumentation-sqlalchemy not installed, skipping")


def _instrument_redis():
    """Instrument Redis client to trace cache operations."""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.debug("OpenTelemetry: Redis instrumented")
    except ImportError:
        logger.warning("opentelemetry-instrumentation-redis not installed, skipping")


def _instrument_celery():
    """Instrument Celery to propagate trace context through async tasks."""
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.debug("OpenTelemetry: Celery instrumented")
    except ImportError:
        logger.warning("opentelemetry-instrumentation-celery not installed, skipping")


def get_tracer(name: str = "queue-management"):
    """
    Get a named tracer for manual instrumentation.

    Usage:
        from app.core.tracing import get_tracer
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("my-operation") as span:
            span.set_attribute("key", "value")
            # ... do work
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        # Return a no-op tracer if OTel is not installed
        class _NoopTracer:
            class _NoopSpan:
                def set_attribute(self, *a, **kw): pass
                def set_status(self, *a, **kw): pass
                def record_exception(self, *a, **kw): pass
                def __enter__(self): return self
                def __exit__(self, *a): pass

            def start_as_current_span(self, name, **kw):
                return self._NoopSpan()

        return _NoopTracer()
