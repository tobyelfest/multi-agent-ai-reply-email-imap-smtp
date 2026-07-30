"""Main worker process that polls the inbox, processes emails, and sends replies."""

import signal
import time
import sys
import logging
from typing import Optional

from config import Settings
from services.email_service import EmailService
from graph.workflow import workflow
from agents.llm import RetryingLLM
from langchain_groq import ChatGroq
from utils.logger import configure_logging


# Global references for cleanup
service: Optional[EmailService] = None
running = True


def signal_handler(sig, frame) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global running
    running = False
    logger.info("Received shutdown signal, exiting gracefully...")


def is_sender_ignored(sender: str, settings: Settings) -> bool:
    """Check if sender should be ignored based on configured lists."""
    if not sender:
        return True
    sender_lower = sender.lower()
    for domain in settings.ignore_domains:
        if domain in sender_lower:
            return True
    for word in settings.ignore_senders:
        if word in sender_lower:
            return True
    return False


def is_email_relevant(subject: str, body: str, settings: Settings, retrying_llm: RetryingLLM) -> tuple[bool, str]:
    """Determine relevance using keyword matching and AI fallback."""
    subject_lower = subject.lower()
    body_lower = body.lower()
    for kw in settings.relevance_keywords:
        if kw in subject_lower or kw in body_lower:
            return True, "keyword_match"

    # AI classification
    prompt = f"""
    Anda adalah asisten customer service untuk perusahaan yang menjual produk fisik.
    Tugas Anda: tentukan apakah email berikut berisi pertanyaan tentang:
    - Stok/ketersediaan produk
    - Harga produk
    - Pemesanan/pembelian produk
    - Informasi produk secara umum

    Jika YA, balas dengan "RELEVAN".
    Jika TIDAK, balas dengan "TIDAK_RELEVAN".

    Email:
    Subject: {subject}
    Body: {body}
    """
    try:
        response = retrying_llm.invoke(prompt)
        answer = response.strip().upper()
        return ("RELEVAN" in answer), "ai_classified"
    except Exception as e:
        logger.error("AI classification failed: %s", e)
        return False, "ai_error"


def send_fallback_reply(email, service: EmailService, settings: Settings) -> None:
    """Send a fallback reply when AI processing fails or email is irrelevant."""
    try:
        service.send_reply(email, settings.fallback_reply_template)
        service.record_processed(email)
        service.mark_as_read(email)
        logger.info("Fallback reply sent to %s", email.sender)
    except Exception as e:
        logger.error("Failed to send fallback reply: %s", e)


def process_emails(service: EmailService, settings: Settings, retrying_llm: RetryingLLM) -> None:
    """Fetch and process new emails."""
    # Try UNSEEN first
    emails = service.fetch_unread_emails()
    if not emails:
        logger.info("No UNSEEN emails. Fetching recent unprocessed (24h)...")
        emails = service.fetch_recent_unprocessed_emails(hours=24)
    if not emails:
        logger.info("No new emails to process.")
        return

    for email in emails:
        logger.info("Processing email from %s | Subject: %s", email.sender, email.subject)

        if is_sender_ignored(email.sender, settings):
            logger.info("Ignoring sender: %s", email.sender)
            service.record_processed(email)
            service.mark_as_read(email)
            continue

        relevant, reason = is_email_relevant(email.subject, email.body, settings, retrying_llm)
        if not relevant:
            logger.info("Email not relevant (%s). Sending fallback.", reason)
            send_fallback_reply(email, service, settings)
            continue

        logger.info("Email relevant (%s). Invoking AI workflow.", reason)
        try:
            initial_state = {
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "message_id": email.message_id,
                "analysis": None,
                "sentiment": None,
                "context": None,
                "draft_reply": None,
                "final_reply": None,
            }
            result = workflow.invoke(initial_state)
            final_reply = result.get("final_reply") or result.get("draft_reply")
            if final_reply:
                service.send_reply(email, final_reply)
                service.record_processed(email)
                service.mark_as_read(email)
                logger.info("AI reply sent to %s", email.sender)
            else:
                logger.warning("No reply generated. Sending fallback.")
                send_fallback_reply(email, service, settings)
        except Exception as e:
            logger.error("Workflow error for %s: %s", email.sender, e)
            send_fallback_reply(email, service, settings)


def main():
    global service, running

    settings = Settings()
    logger.info("Starting AI Email Auto Reply worker...")

    # Initialize LLM for relevance classification
    llm = ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0.0,
        max_retries=0,
    )
    retrying_llm = RetryingLLM(
        llm,
        retries=settings.llm_retries,
        retry_base_seconds=settings.retry_base_seconds,
        logger=logger,
    )

    service = EmailService(settings, logger)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        try:
            process_emails(service, settings, retrying_llm)
        except Exception as e:
            logger.error("Worker loop error: %s", e)
        if running:
            time.sleep(settings.check_interval)

    # Cleanup
    if service:
        service.close()
    logger.info("Worker stopped.")


if __name__ == "__main__":
    logger = configure_logging(Settings().log_dir)
    main()
