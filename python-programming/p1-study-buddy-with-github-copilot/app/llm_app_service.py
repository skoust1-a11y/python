"""Service functions for prompt creation and Gemini/OpenAI interactions."""

from collections.abc import Iterator


def build_explanation_prompt(concept: str) -> str:
    """Build a consistent tutoring prompt for the requested concept."""
    return f"Explain {concept} in Agentic AI clearly and concisely for a beginner."


def generate_explanation(client, model: str, concept: str) -> str:
    """Call the chat completion API and return a single explanation string."""
    prompt = build_explanation_prompt(concept)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_explanation_stream(client, model: str, concept: str) -> Iterator[str]:
    """Yield explanation text chunks from a streaming chat completion call."""
    prompt = build_explanation_prompt(concept)
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
