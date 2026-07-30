"""IMAP client with automatic reconnect, health checks, and retries."""

import imaplib
import time
import logging
from typing import List, Optional, Union

from core.retry import retry


class IMAPClient:
    """Encapsulates IMAP connection and operations with reconnect logic."""

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
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger = logger.getChild("imap")
        self.timeout = timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    @property
    def connection(self) -> imaplib.IMAP4_SSL:
        """Ensure connection is active and return it."""
        if self._connection is None:
            self._connect()
        else:
            try:
                self._connection.noop()
            except Exception:
                self.logger.warning("IMAP connection unhealthy, reconnecting...")
                self._connect()
        return self._connection

    def _connect(self) -> None:
        """Establish IMAP connection with retries."""
        attempt = 1
        while True:
            try:
                self._connection = imaplib.IMAP4_SSL(self.host, self.port, timeout=self.timeout)
                self._connection.login(self.username, self.password)
                self._connection.select("INBOX")
                self.logger.info("IMAP connected to %s:%d", self.host, self.port)
                return
            except Exception as exc:
                if attempt >= self.max_reconnect_attempts:
                    self.logger.error("Failed to connect IMAP after %d attempts", attempt)
                    raise
                self.logger.warning(
                    "IMAP connection attempt %d failed: %s. Retrying in %ds",
                    attempt, exc, attempt * 2
                )
                time.sleep(attempt * 2)
                attempt += 1

    def close(self) -> None:
        """Close IMAP connection if open."""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    @retry(
        exceptions=(imaplib.IMAP4.error, BrokenPipeError, ConnectionError, TimeoutError),
        max_attempts=3,
        base_delay=1.0,
        backoff=2.0,
        logger=None,
        raise_on_failure=True,
    )
    def _search(self, criteria: str) -> List[bytes]:
        conn = self.connection
        status, data = conn.search(None, criteria)
        if status != "OK":
            raise imaplib.IMAP4.error(f"Search failed: {status}")
        return data[0].split() if data[0] else []

    def search_unread(self) -> List[bytes]:
        """Return UIDs of unread messages."""
        return self._search("UNSEEN")

    def search_since(self, since_date: str) -> List[bytes]:
        """Return UIDs of messages since given date (format: dd-MMM-yyyy)."""
        return self._search(f'SINCE "{since_date}"')

    def fetch_raw(self, uid: Union[bytes, str]) -> Optional[bytes]:
        """Fetch raw RFC822 message for given UID."""
        if isinstance(uid, str):
            uid = uid.encode()
        conn = self.connection
        try:
            status, data = conn.fetch(uid, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                return None
            return data[0][1]
        except Exception as exc:
            self.logger.error("Fetch UID %s failed: %s", uid, exc)
            return None

    def mark_seen(self, uid: Union[bytes, str]) -> bool:
        """Mark message with given UID as \\Seen."""
        if isinstance(uid, str):
            uid = uid.encode()
        conn = self.connection
        try:
            conn.store(uid, "+FLAGS", "\\Seen")
            return True
        except Exception as exc:
            self.logger.error("Mark UID %s as seen failed: %s", uid, exc)
            return False
