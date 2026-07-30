"""Analyzer node for the unchanged first stage of the reply workflow."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import RetryingLLM
from graph.state import EmailWorkflowState


def build_analyzer_agent(llm: RetryingLLM):
    """Build the Analyzer node.

    Args:
        llm: RetryingLLM instance.

    Returns:
        Callable node function.
    """

    def analyze(state: EmailWorkflowState) -> dict[str, str]:
        """Perform analysis on the incoming email."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the Analyzer Agent in a customer-email workflow. "
                        "Identify the customer's request, key facts, constraints, and any "
                        "questions that need an answer. Do not draft the reply."
                    )
                ),
                HumanMessage(
                    content=(
                        f"From: {state['sender']}\nSubject: {state['subject']}\n\n"
                        f"Email body:\n{state['body']}"
                    )
                ),
            ]
        )
        return {"analysis": response}

    return analyze
