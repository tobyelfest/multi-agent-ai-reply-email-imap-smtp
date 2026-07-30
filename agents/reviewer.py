"""Reviewer node for the final stage of the reply workflow."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import RetryingLLM
from graph.state import EmailWorkflowState


def build_reviewer_agent(llm: RetryingLLM):
    """Build the Reviewer node.

    Args:
        llm: RetryingLLM instance.

    Returns:
        Callable node function.
    """

    def review_reply(state: EmailWorkflowState) -> dict[str, str]:
        """Review and refine the draft, returning the final email body."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the Reviewer Agent in a customer-email workflow. "
                        "Check the draft for accuracy, clarity, courtesy, and safe claims. "
                        "Return only the final email body, with no review commentary or labels."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Original customer email:\n{state['body']}\n\n"
                        f"Retrieved context:\n{state['context']}\n\n"
                        f"Draft reply:\n{state['draft_reply']}"
                    )
                ),
            ]
        )
        return {"final_reply": response}

    return review_reply
