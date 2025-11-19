"""
Observability setup using Langfuse @observe decorator and OpenTelemetry.
"""
from langfuse import observe, get_client
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


## Task 1: Setup OpenTelemetry Tracer Provider and add ConsoleSpanExporter




