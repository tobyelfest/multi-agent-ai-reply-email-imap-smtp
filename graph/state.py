"""State schema shared by the fixed LangGraph workflow nodes."""

from __future__ import annotations

from typing import TypedDict, Optional


class EmailWorkflowState(TypedDict, total=False):
    """Data passed through Analyzer → Sentiment → Context → Drafter → Reviewer."""

    sender: str
    subject: str
    body: str
    message_id: str
    analysis: str
    sentiment: str
    context: str
    draft_reply: str
    final_reply: str
