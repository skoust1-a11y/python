"""LlamaIndex response synthesizer with source-aware generation."""

from llama_index.core.llms import ChatMessage, LLM, MessageRole
from llama_index.core.response_synthesizers import ResponseMode, get_response_synthesizer
from llama_index.core.schema import NodeWithScore

from app.prompts.templates import HYBRID_QA_PROMPT_TEMPLATE, LEGAL_ANALYSIS_SYSTEM_PROMPT
from app.rag.prompt_template import LEGAL_QA_PROMPT, LEGAL_REFINE_PROMPT


class LegalResponseSynthesizer:
    """Wrap LlamaIndex synthesizers for grounded legal Q&A."""

    def __init__(self, llm: LLM) -> None:
        self._llm = llm
        self._synthesizer = get_response_synthesizer(
            llm=llm,
            response_mode=ResponseMode.COMPACT,
            text_qa_template=LEGAL_QA_PROMPT,
            refine_template=LEGAL_REFINE_PROMPT,
            use_async=True,
        )

    @property
    def llm(self) -> LLM:
        return self._llm

    async def synthesize(self, question: str, nodes: list[NodeWithScore]) -> str:
        """Generate a grounded answer from retrieved nodes."""
        if not nodes:
            return (
                "I could not find relevant information in the indexed documents to "
                "answer this question. Please ensure documents are uploaded and indexed."
            )

        response = await self._synthesizer.asynthesize(question, nodes=nodes)
        return str(response).strip()

    async def synthesize_from_context(self, question: str, context_text: str) -> str:
        """Generate an answer from pre-built context (hybrid / SQL paths)."""
        if not context_text.strip():
            return (
                "I could not find relevant structured or document information to "
                "answer this question."
            )

        user_content = HYBRID_QA_PROMPT_TEMPLATE.format(
            context=context_text,
            question=question,
        )
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=LEGAL_ANALYSIS_SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=user_content),
        ]
        response = await self._llm.achat(messages)
        return (response.message.content or "").strip()
