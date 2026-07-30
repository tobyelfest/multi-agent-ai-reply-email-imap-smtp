"""Drafter node for the fourth stage of the reply workflow."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import RetryingLLM
from graph.state import EmailWorkflowState


def build_drafter_agent(llm: RetryingLLM):
    """Build the Drafter node.

    Args:
        llm: RetryingLLM instance.

    Returns:
        Callable node function.
    """

    def draft_reply(state: EmailWorkflowState) -> dict[str, str]:
        """Generate an initial draft reply based on analysis and context."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the Drafter Agent in a customer-email workflow. "
                        "Write a helpful, accurate, concise email reply. Use only confirmed "
                        "context; do not invent policies, timelines, or commitments."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Customer email:\n{state['body']}\n\n"
                        f"Analyzer notes:\n{state['analysis']}\n\n"
                        f"Sentiment guidance:\n{state['sentiment']}\n\n"
                        f"Retrieved context:\n{state['context']}"
                    )
                ),
            ]
        )
        return {"draft_reply": response}

    return draft_reply
