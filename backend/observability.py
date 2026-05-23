"""
Observability setup using Langfuse @observe decorator and OpenTelemetry.
"""
from langfuse import observe, get_client
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


## Task 1: Setup OpenTelemetry Tracer Provider and add ConsoleSpanExporter

def intialize_opentelemetry():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

intialize_opentelemetry()

def flush_langfuse():
    try:
        get_client().flush()
    except Exception as e:
        pass

__all__ = ['observe','flush_langfuse','intialize_opentelemetry']


