"""OpenTelemetry-ready tracing helpers."""

import contextvars
import functools
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

P = ParamSpec("P")
T = TypeVar("T")

_current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "vrag_trace_id",
    default="",
)
_telemetry_initialized = False


def traced(name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorate sync or async functions with a lightweight named span log."""

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        log = logging.getLogger("vrag.trace")

        if inspect.iscoroutinefunction(fn):
            async_fn = cast(Callable[P, Awaitable[Any]], fn)

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                log.info("span.start name=%s trace_id=%s", name, _current_trace_id.get())
                return await async_fn(*args, **kwargs)

            return cast(Callable[P, T], async_wrapper)

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            log.info("span.start name=%s trace_id=%s", name, _current_trace_id.get())
            return fn(*args, **kwargs)

        return sync_wrapper

    return decorator


def init_telemetry(otel_endpoint: str = "") -> None:
    """Initialize OpenTelemetry tracing once for the process."""

    global _telemetry_initialized
    if _telemetry_initialized:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    if otel_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint))
        )
    trace.set_tracer_provider(provider)
    _telemetry_initialized = True
