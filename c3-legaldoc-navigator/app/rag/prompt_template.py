"""LlamaIndex prompt templates for legal RAG synthesis."""

from llama_index.core.prompts import PromptTemplate

from app.prompts.templates import LEGAL_ANALYSIS_SYSTEM_PROMPT, RAG_USER_PROMPT_TEMPLATE

LEGAL_QA_PROMPT = PromptTemplate(
    RAG_USER_PROMPT_TEMPLATE,
)

LEGAL_REFINE_PROMPT = PromptTemplate(
    "We have an existing answer: {existing_answer}\n"
    "We have additional context:\n{context}\n"
    "Refine the answer to incorporate the new context. "
    "Preserve source citations where possible.\n"
    "Question: {query}\n"
    "Refined answer:"
)


def build_chat_messages(question: str, context: str) -> list[dict[str, str]]:
    """Build provider-agnostic chat messages for direct LLM completion."""
    user_content = RAG_USER_PROMPT_TEMPLATE.format(context=context, question=question)
    return [
        {"role": "system", "content": LEGAL_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
