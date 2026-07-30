"""SMTP client with automatic reconnect, fallback ports, and retries."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from typing import Optional

from core.retry import retry


class SMTPClient:
    """Encapsulates SMTP connection and sending with reconnect logic."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        logger: logging.Logger,
        *,
        timeout: int = 30,
        max_reconnect_attempts: int = 3,
        fallback_ports: Optional[list] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger = logger.getChild("smtp")
        self.timeout = timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.fallback_ports = fallback_ports or [587, 465]
        self._connection: Optional[smtplib.SMTP] = None
        self._connected_port: Optional[int] = None

    @property
    def connection(self) -> smtplib.SMTP:
        """Ensure connection is active and return it."""
        if self._connection is None:
            self._connect()
        else:
            try:
                self._connection.noop()
            except Exception:
                self.logger.warning("SMTP connection unhealthy, reconnecting...")
                self._connect()
        return self._connection

    def _connect(self) -> None:
        """Establish SMTP connection trying SSL and STARTTLS."""
        attempts = [self.port] + [p for p in self.fallback_ports if p != self.port]
        for port in attempts:
            try:
                if port == 465:
                    conn = smtplib.SMTP_SSL(self.host, port, timeout=self.timeout)
                else:
                    conn = smtplib.SMTP(self.host, port, timeout=self.timeout)
                    conn.starttls()
                conn.login(self.username, self.password)
                self._connection = conn
                self._connected_port = port
                self.logger.info("SMTP connected to %s:%d (SSL=%s)", self.host, port, port == 465)
                return
            except Exception as exc:
                self.logger.warning("SMTP connection to %s:%d failed: %s", self.host, port, exc)
                continue
        raise RuntimeError(f"SMTP connection failed on all ports: {attempts}")

    def close(self) -> None:
        """Close SMTP connection if open."""
        if self._connection:
            try:
                self._connection.quit()
            except Exception:
                pass
            self._connection = None
            self._connected_port = None

    @retry(
        exceptions=(smtplib.SMTPException, BrokenPipeError, ConnectionError, TimeoutError),
        max_attempts=3,
        base_delay=1.0,
        backoff=2.0,
        logger=None,
        raise_on_failure=True,
    )
    def send_email(
        self,
        from_addr: str,
        to_addr: str,
        subject: str,
        body: str,
        *,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> None:
        """Send an email via SMTP."""
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
        msg["Date"] = formatdate()
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        msg.attach(MIMEText(body, "plain", "utf-8"))

        conn = self.connection
        conn.sendmail(from_addr, to_addr, msg.as_string())
        self.logger.info("Email sent to %s", to_addr)
