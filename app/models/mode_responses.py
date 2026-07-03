"""Multi-mode response container."""

from __future__ import annotations

from dataclasses import dataclass

from app.prompts.types import RESPONSE_MODES, ResponseMode


@dataclass(frozen=True)
class ModeResponses:
    strict: str
    explain: str
    analysis: str

    def as_dict(self) -> dict[ResponseMode, str]:
        return {
            "strict": self.strict,
            "explain": self.explain,
            "analysis": self.analysis,
        }

    def get(self, mode: str) -> str:
        return self.as_dict()[mode]  # type: ignore[index]

    @classmethod
    def from_dict(cls, responses: dict[str, str]) -> ModeResponses:
        return cls(
            strict=responses["strict"],
            explain=responses["explain"],
            analysis=responses["analysis"],
        )

    @classmethod
    def uniform(cls, text: str) -> ModeResponses:
        return cls(strict=text, explain=text, analysis=text)


def empty_mode_responses(*, strict_message: str, default_message: str) -> ModeResponses:
    """Build mode responses when retrieval returned no usable context."""
    return ModeResponses(
        strict=strict_message,
        explain=default_message,
        analysis=default_message,
    )


ALL_MODES: tuple[ResponseMode, ...] = RESPONSE_MODES
