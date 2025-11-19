"""
Langfuse Callback Handler Module

This module provides a centralized Langfuse callback handler for tracing
LangChain chain executions in the Langfuse dashboard.
"""
import os
from typing import Optional
from langfuse.langchain import CallbackHandler
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()

## Task 2: Add Observability with Langfuse Callback Handler (Chat API)
