"""Mock RAG service boundary.

Replace the sample corpus with the project's existing mock-RAG implementation.
The public `retrieve` contract intentionally remains small so the graph does not
need to change when a real vector store is introduced later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(slots=True)
class MockRAGService:
    """A lightweight in-memory retrieval implementation for local development."""

    documents: Sequence[str] = field(
        default_factory=lambda: (
            "Support hours are Monday to Friday, 09:00 to 17:00 local time.",
            "For account-security requests, ask the customer to use the verified support channel.",
            "Do not promise refunds, dates, or policy exceptions unless the knowledge base confirms them.",
        )
    )

    def retrieve(self, query: str, *, limit: int = 3) -> list[str]:
        """Return the most relevant mock documents using simple token overlap."""
        query_tokens = set(query.lower().split())
        scored = []
        for document in self.documents:
            score = len(query_tokens.intersection(document.lower().split()))
            scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored[:limit]]
