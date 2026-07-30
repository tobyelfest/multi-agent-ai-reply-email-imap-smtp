"""Context node that calls the existing Mock RAG service."""

from __future__ import annotations

from agents.llm import RetryingLLM
from graph.state import EmailWorkflowState
from services.rag_service import MockRAGService


def build_context_agent(rag_service: MockRAGService, _llm: RetryingLLM):
    """Build the Context node using the mock-RAG contract.

    Args:
        rag_service: MockRAGService instance.
        _llm: RetryingLLM (unused, kept for uniform dependency injection).

    Returns:
        Callable node function.
    """

    def retrieve_context(state: EmailWorkflowState) -> dict[str, str]:
        """Retrieve relevant context documents based on email content."""
        query = f"{state['subject']}\n{state['body']}\n{state['analysis']}"
        documents = rag_service.retrieve(query)
        context = "\n\n".join(f"- {document}" for document in documents)
        return {"context": context or "No matching mock-RAG context was found."}

    return retrieve_context
