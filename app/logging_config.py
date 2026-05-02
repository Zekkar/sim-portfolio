"""
sim-portfolio 結構化日誌設定（STANDARDS.md §3.1）

輸出：純 stdout JSON（12-factor app）
格式：每行一個 JSON 物件，含 timestamp / level / event / Application 欄位
不做任何 HTTP push（無 SeqSink、無 LokiSink）
"""

import os
import logging
import sys

import structlog


_service_name: str = "sim-portfolio"


def _add_application(logger, method_name, event_dict):
    """處理器：注入 Application 欄位（對應 Loki label）"""
    event_dict["Application"] = _service_name
    return event_dict


def _add_trace_context(logger, method_name, event_dict):
    """處理器：注入 OpenTelemetry TraceId / SpanId

    Grafana Trace↔Log 跳轉依賴此欄位，必須與 telemetry_config.py 搭配使用。
    """
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id != 0:
            event_dict["TraceId"] = format(ctx.trace_id, "032x")
            event_dict["SpanId"] = format(ctx.span_id, "016x")
    except ImportError:
        pass  # OTel 未安裝時靜默跳過
    return event_dict


def _normalize_level(logger, method_name, event_dict):
    """確保 level 為大寫（STANDARDS.md §3.1 規定）"""
    if "level" in event_dict:
        event_dict["level"] = str(event_dict["level"]).upper()
    return event_dict


def setup_logging(service_name: str = "sim-portfolio") -> None:
    """初始化結構化日誌系統（合規版本）

    Args:
        service_name: 服務名稱，會作為 Application 欄位（Loki label）

    Example:
        from app.logging_config import setup_logging
        setup_logging("sim-portfolio")

        import logging
        logger = logging.getLogger(__name__)
        logger.info("server started")
        # stdout: {"timestamp":"...","level":"INFO","event":"server started","Application":"sim-portfolio"}
    """
    global _service_name
    _service_name = service_name

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # === 標準 processor chain（STANDARDS.md §3.1）===
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_trace_context,     # 注入 TraceId / SpanId
        _add_application,       # 注入 Application
        _normalize_level,       # level 大寫
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 讓 stdlib logging 也走完整 processor chain
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)  # 12-factor: stdout
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 第三方套件降噪
    for noisy in ["urllib3", "asyncio", "httpx", "httpcore", "uvicorn.access"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
