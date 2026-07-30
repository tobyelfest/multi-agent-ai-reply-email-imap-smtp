"""LangGraph workflow definition with the fixed linear pipeline."""

from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from agents.analyzer import build_analyzer_agent
from agents.context import build_context_agent
from agents.drafter import build_drafter_agent
from agents.llm import RetryingLLM
from agents.reviewer import build_reviewer_agent
from agents.sentiment import build_sentiment_agent
from config import Settings
from graph.state import EmailWorkflowState
from services.rag_service import MockRAGService


def build_workflow(settings: Settings, logger: logging.Logger) -> Any:
    """Compile the existing linear workflow without any email-provider dependency.

    The sequence is intentionally fixed:
    Analyzer → Sentiment → Context → Drafter → Reviewer
    """
    llm = ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0.2,
        max_retries=0,
    )

    retrying_llm = RetryingLLM(
        llm,
        retries=settings.llm_retries,
        retry_base_seconds=settings.retry_base_seconds,
        logger=logger,
    )

    rag_service = MockRAGService()

    graph = StateGraph(EmailWorkflowState)

    graph.add_node("analyzer", build_analyzer_agent(retrying_llm))
    graph.add_node("sentiment", build_sentiment_agent(retrying_llm))
    graph.add_node("context", build_context_agent(rag_service, retrying_llm))
    graph.add_node("drafter", build_drafter_agent(retrying_llm))
    graph.add_node("reviewer", build_reviewer_agent(retrying_llm))

    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "sentiment")
    graph.add_edge("sentiment", "context")
    graph.add_edge("context", "drafter")
    graph.add_edge("drafter", "reviewer")
    graph.add_edge("reviewer", END)

    return graph.compile()


# Singleton instance for compatibility with existing imports
from config import Settings
from utils.logger import configure_logging

_settings = Settings()
_logger = configure_logging(_settings.log_dir)
workflow = build_workflow(_settings, _logger)
