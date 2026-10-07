"""Small observable HTTP service for a local GitOps portfolio lab."""
import json
import logging
import os
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace

REQUESTS = Counter("portfolio_requests_total", "Completed requests", ["route", "status"])
LATENCY = Histogram("portfolio_request_duration_seconds", "Request latency", ["route"])
LOGGER = logging.getLogger("portfolio")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())


def configure_telemetry(app):
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

    resource = Resource.create({"service.name": "portfolio-api", "service.version": os.getenv("APP_VERSION", "v1")})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FlaskInstrumentor().instrument_app(app, excluded_urls="healthz,readyz,metrics")
    logs = LoggerProvider(resource=resource)
    logs.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    LOGGER.addHandler(LoggingHandler(logger_provider=logs))


def create_app():
    app = Flask(__name__)
    configure_telemetry(app)

    @app.before_request
    def start_timer():
        g.started = time.monotonic()

    @app.after_request
    def observe(response):
        route = request.url_rule.rule if request.url_rule else "unmatched"
        if route not in ("/metrics", "/healthz", "/readyz"):
            elapsed = time.monotonic() - g.started
            REQUESTS.labels(route, str(response.status_code)).inc()
            LATENCY.labels(route).observe(elapsed)
            context = trace.get_current_span().get_span_context()
            trace_id = format(context.trace_id, "032x")
            response.headers["X-Trace-ID"] = trace_id
            LOGGER.info(json.dumps({"route": route, "status": response.status_code, "duration_ms": round(elapsed * 1000, 2), "trace_id": trace_id}))
        return response

    @app.get("/")
    def index():
        return jsonify(service="portfolio-api", version=os.getenv("APP_VERSION", "v1"), message="Delivered through GitOps")

    @app.get("/healthz")
    @app.get("/readyz")
    def health():
        return jsonify(status="ok")

    @app.get("/work")
    def work():
        try:
            delay = int(request.args.get("delay_ms", "50"))
        except ValueError:
            return jsonify(error="delay_ms must be an integer"), 400
        if not 0 <= delay <= 2000:
            return jsonify(error="delay_ms must be between 0 and 2000"), 400
        with trace.get_tracer(__name__).start_as_current_span("simulate-work"):
            time.sleep(delay / 1000)
        return jsonify(delay_ms=delay, result="completed")

    @app.get("/error")
    def controlled_error():
        return jsonify(error="Intentional failure for observability exercises"), 500

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    return app


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 8080, create_app(), threaded=True, use_reloader=False)
