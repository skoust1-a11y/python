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

### 1. Code Issue Detection
- Accept code input via text or file upload.  
- Analyze and detect syntax errors, logic flaws, and inefficient patterns.  
- Identify complex or unclear sections in the code.  

### 2. Code Context Awareness
- Understand the programming language, coding style, and skill level of the user.  
- Interpret the purpose of the code to provide meaningful explanations.  
- Adapt responses based on the user's experience level and learning progress.

### 3. Code Improvement Recommendation System
Recommends actions such as:

- Human-friendly explanations of code logic and structure.  
- Step-by-step debugging insights and improved code versions.  
- Optimization suggestions for cleaner, faster, and maintainable code.  
- Reusable code snippets (e.g., API calls, loops, class templates).  
- Function/class templates relevant to the current problem.  

Also includes:

- User feedback options: “Helpful” / “Not Helpful”.  
- Continuous learning loop to refine future recommendations.

### 4. AI Integration

- Use **LLM Models** for dynamic and personalized well-being activity generation.

---

## Technical Details

**Programming Language:** Python

### Libraries & Tools

| Library/Tool | Purpose |
|-------------|---------|
| `fastapi`   | Build backend API |
| `uvicorn`   | Run FastAPI server |
| `requests`  | Communicate with Gemini / Ollama APIs |
| `dotenv`    | Manage environment variables securely |

### Environment Variables

| Variable | Purpose |
|---------|---------|
| `GEMINI_API_KEY` | Authenticate requests to Gemini API |
| `OLLAMA_MODEL_PATH` | Path to local Ollama model instance |
