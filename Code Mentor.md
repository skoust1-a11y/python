# Code Mentor – Your AI Pair Programmer

An intelligent coding companion that assists developers by explaining code, suggesting improvements, generating snippets, debugging errors, and guiding best practices in real-time.

## Problem Statement: Code Mentor – Your AI Pair Programmer

### Context

Developers at all experience levels often struggle with debugging issues, understanding unfamiliar code patterns, and remembering best practices across frameworks and languages. While tutorials and documentation exist, they are often lengthy, generic, and time-consuming to reference during active development.

Common challenges include:

- **Debugging Overload:** Identifying the root cause of errors can consume significant time.
- **Learning Curve Barriers:** New developers find it overwhelming to understand advanced patterns, APIs, and frameworks.
- **Knowledge Gaps in Best Practices:** Writing code that is functional, clean, and secure is difficult without guidance.
- **Context Switching:** Searching online for solutions interrupts focus and productivity.
- **Limited Real-Time Help:** Developers need suggestions *while* coding, not after the fact.

This project introduces **Code Mentor**, an **AI-powered pair programmer** that supports developers in real-time through code comprehension, fixes, improvements, and contextual explanations.

## Problem Description

The goal of this project is to build a **Python-based Code Mentor Application** that:

- Understands and analyzes input code (Python, Java, JavaScript, etc.).
- Suggests context-aware improvements and bug fixes.
- Provides simplified explanations of complex code blocks.
- Recommends best practices and alternative implementations.
- Learns user coding style over time to provide personalized suggestions.

## Functional Requirements

### 1. Code Understanding & Explanation

- Accept code input via text or file upload.
- Generate human-friendly explanations of logic and structure.
- Highlight complex or inefficient sections.

### 2. Debugging Assistance

- Detect common syntax and logic errors.
- Suggest step-by-step solutions or improved versions of the code.

### 3. Code Optimization & Best Practices

- Recommend cleaner, faster, and more maintainable code.
- Share best practices based on developer skill level and language conventions.

### 4. Snippet & Template Recommendation

- Provide reusable code snippets for common tasks (e.g., API calls, loops, class structures).
- Suggest function or class templates relevant to the current problem.

### 5. Learning Feedback Loop

- Allow users to mark suggestions as “helpful” or “not helpful”.
- Adapt future recommendations based on feedback patterns.

## AI Integration

- Utilize **LLM models** to analyze and generate code explanations and improvements.
- Maintain history to refine suggestions according to user’s past coding sessions.

## Technical Details

**Programming Language:** Python

**Libraries/Tools:**

| Tool / Library | Purpose |
|---|---|
| **FastAPI** | Backend API services |
| **Uvicorn** | Server execution |
| **Pydantic** | Request/response validation |
| **Requests** | Communication with AI model APIs |
| **python-dotenv** | Secure environment variable handling |

**Environment Variables:**

| Variable Name | Purpose |
|---|---|
| `GEMINI_API_KEY` | Authentication for Gemini AI model |
| `OLLAMA_MODEL_PATH` | Path for local Ollama model instance |
