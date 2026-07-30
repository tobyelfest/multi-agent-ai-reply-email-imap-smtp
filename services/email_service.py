"""Email service providing the public API used by main.py and api.py.

This module exposes the same interface as before:
- fetch_unread_emails()
- fetch_recent_unprocessed_emails(hours)
- send_reply(email, reply)
- record_processed(email)
- mark_as_read(email)
"""

import logging
import smtplib  # <-- TAMBAHKAN INI
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from config import Settings
from core.imap_client import IMAPClient
from core.smtp_client import SMTPClient
from core.email_parser import EmailParser
from core.processed_storage import ProcessedStorage
from core.retry import retry, RetryError


@dataclass
class InboundEmail:
    """Immutable email object used by the public API."""
    imap_uid: str
    sender: str
    subject: str
    body: str
    message_id: str
    in_reply_to: Optional[str] = None
    references: Optional[str] = None


class EmailService:
    """Production-grade email service with IMAP/SMTP clients and storage."""

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger.getChild("email_service")

        self.imap = IMAPClient(
            host=settings.imap_server,
            port=settings.imap_port,
            username=settings.email_address,
            password=settings.email_app_password,
            logger=self.logger,
        )
        self.smtp = SMTPClient(
            host=settings.smtp_server,
            port=settings.smtp_port,
            username=settings.email_address,
            password=settings.email_app_password,
            logger=self.logger,
        )
        self.storage = ProcessedStorage(settings.processed_storage_file)
        self.parser = EmailParser()

    def _fetch_email_by_uid(self, uid: bytes) -> Optional[InboundEmail]:
        """Fetch and parse a single email by UID."""
        raw = self.imap.fetch_raw(uid)
        if not raw:
            return None
        parsed = self.parser.parse_raw(raw)
        return InboundEmail(
            imap_uid=uid.decode(),
            sender=parsed["sender"],
            subject=parsed["subject"],
            body=parsed["body"],
            message_id=parsed["message_id"],
            in_reply_to=parsed["in_reply_to"],
            references=parsed["references"],
        )

    def _fetch_emails_by_uids(self, uids: List[bytes]) -> List[InboundEmail]:
        """Fetch multiple emails by UIDs."""
        result = []
        for uid in uids:
            email_obj = self._fetch_email_by_uid(uid)
            if email_obj:
                result.append(email_obj)
        return result

    # ----- Public API (unchanged signatures) -----

    @retry(
        exceptions=(RetryError, ConnectionError, TimeoutError),
        max_attempts=2,
        base_delay=1.0,
        backoff=2.0,
        logger=None,
        raise_on_failure=False
    )
    def fetch_unread_emails(self) -> List[InboundEmail]:
        """Fetch all unread emails from the inbox."""
        try:
            uids = self.imap.search_unread()
            self.logger.info("Fetched %d UNSEEN UIDs", len(uids))
            if not uids:
                return []
            return self._fetch_emails_by_uids(uids)
        except Exception as exc:
            self.logger.error("fetch_unread_emails failed: %s", exc)
            return []

    @retry(
        exceptions=(RetryError, ConnectionError, TimeoutError),
        max_attempts=2,
        base_delay=1.0,
        backoff=2.0,
        raise_on_failure=False
    )
    def fetch_recent_unprocessed_emails(self, hours: int = 24) -> List[InboundEmail]:
        """Fetch emails from the last N hours that have not been processed."""
        try:
            since_date = (datetime.now() - timedelta(hours=hours)).strftime("%d-%b-%Y")
            uids = self.imap.search_since(since_date)
            self.logger.info("Fetched %d UIDs since %s", len(uids), since_date)
            if not uids:
                return []

            emails = []
            for uid in uids:
                parsed = self.parser.parse_raw(self.imap.fetch_raw(uid))
                if not parsed:
                    continue
                if not self.storage.contains_with_fallback(
                    parsed["message_id"],
                    parsed["sender"],
                    parsed["subject"],
                    parsed["body"]
                ):
                    emails.append(
                        InboundEmail(
                            imap_uid=uid.decode(),
                            sender=parsed["sender"],
                            subject=parsed["subject"],
                            body=parsed["body"],
                            message_id=parsed["message_id"],
                            in_reply_to=parsed["in_reply_to"],
                            references=parsed["references"],
                        )
                    )
            return emails
        except Exception as exc:
            self.logger.error("fetch_recent_unprocessed_emails failed: %s", exc)
            return []

    @retry(
        exceptions=(RetryError, ConnectionError, TimeoutError, smtplib.SMTPException),
        max_attempts=3,
        base_delay=1.0,
        backoff=2.0,
        raise_on_failure=False
    )
    def send_reply(self, email: InboundEmail, reply: str) -> None:
        """Send a reply email via SMTP."""
        try:
            self.smtp.send_email(
                from_addr=self.settings.email_address,
                to_addr=email.sender,
                subject=email.subject,
                body=reply,
                in_reply_to=email.message_id or email.in_reply_to,
                references=email.message_id or email.references,
            )
        except Exception as exc:
            self.logger.error("send_reply to %s failed: %s", email.sender, exc)
            self.logger.info("FALLBACK: would have sent reply to %s", email.sender)

    def record_processed(self, email: InboundEmail) -> None:
        """Record the email as processed using Message-ID or hash."""
        identifier = self.storage.add_with_fallback(
            email.message_id,
            email.sender,
            email.subject,
            email.body
        )
        self.logger.debug("Recorded processed: %s", identifier)

    def mark_as_read(self, email: InboundEmail) -> None:
        """Mark the original email as read in the IMAP inbox."""
        self.imap.mark_seen(email.imap_uid)

    def close(self) -> None:
        """Clean up IMAP and SMTP connections."""
        self.imap.close()
        self.smtp.close()
