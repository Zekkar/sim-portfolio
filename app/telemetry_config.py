"""
sim-portfolio OpenTelemetry 設定（STANDARDS.md §3.2）

service_name="sim-portfolio"、service_namespace="sim-portfolio"
asyncpg instrumentation 預設啟用（此服務直接使用 asyncpg）
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


# ─── 標準預設值（STANDARDS.md §3.5）──────────────────────────────────
_DEFAULT_OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://tempo:4317",
)
_TRACING_ENABLED = os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true"
_ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

_tracer_provider: Optional[TracerProvider] = None


def setup_telemetry(
    service_name: str = "sim-portfolio",
    service_namespace: str = "sim-portfolio",
    app=None,
    enable_redis: bool = False,
    enable_httpx: bool = True,
    enable_asyncpg: bool = True,
) -> None:
    """初始化 OpenTelemetry Tracing（合規版本）

    Args:
        service_name: 服務名稱，對應 Loki Application 欄位
        service_namespace: 專案命名空間
        app: FastAPI 實例，傳入時自動加 instrumentation
        enable_redis: 是否追蹤 Redis（此服務無 Redis，預設 False）
        enable_httpx: 是否追蹤 httpx HTTP 請求
        enable_asyncpg: 是否追蹤 asyncpg PostgreSQL 操作（此服務必須 True）
    """
    global _tracer_provider

    if not _TRACING_ENABLED:
        logging.getLogger(__name__).info(
            "[%s] OpenTelemetry tracing 已停用 (OTEL_TRACING_ENABLED=false)",
            service_name,
        )
        return

    if _tracer_provider is not None:
        return  # 已初始化

    # === 標準 Resource attributes（STANDARDS.md §3.2）===
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": service_namespace,
        "deployment.environment": _ENVIRONMENT,
    })

    _tracer_provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(
        endpoint=_DEFAULT_OTLP_ENDPOINT,
        insecure=True,
    )
    _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(_tracer_provider)

    # === 自動 instrumentation ===
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls="health,healthz,ready,metrics,api/sim/health",
            )
        except ImportError:
            logging.getLogger(__name__).warning(
                "opentelemetry-instrumentation-fastapi 未安裝"
            )

    if enable_redis:
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument()
        except ImportError:
            pass

    if enable_httpx:
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except ImportError:
            pass

    if enable_asyncpg:
        try:
            from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
            AsyncPGInstrumentor().instrument()
        except ImportError:
            logging.getLogger(__name__).warning(
                "opentelemetry-instrumentation-asyncpg 未安裝"
            )

    logging.getLogger(__name__).info(
        "[%s] OpenTelemetry tracing 啟用 → %s",
        service_name,
        _DEFAULT_OTLP_ENDPOINT,
    )


def shutdown_telemetry() -> None:
    """應用關閉時呼叫（flush 未送出的 spans）"""
    global _tracer_provider
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None


def get_tracer(name: str = __name__):
    """取得 Tracer 實例供手動建立 span"""
    return trace.get_tracer(name)
