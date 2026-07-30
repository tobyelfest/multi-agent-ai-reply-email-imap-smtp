"""Sentiment node for the second stage of the reply workflow."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import RetryingLLM
from graph.state import EmailWorkflowState


def build_sentiment_agent(llm: RetryingLLM):
    """Build the Sentiment node.

    Args:
        llm: RetryingLLM instance.

    Returns:
        Callable node function.
    """

    def assess_sentiment(state: EmailWorkflowState) -> dict[str, str]:
        """Assess emotional tone and urgency."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the Sentiment Agent in a customer-email workflow. "
                        "Classify the emotional tone and urgency, then recommend the "
                        "appropriate reply tone. Do not draft the reply."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Customer email:\n{state['body']}\n\n"
                        f"Analyzer notes:\n{state['analysis']}"
                    )
                ),
            ]
        )
        return {"sentiment": response}

    return assess_sentiment
