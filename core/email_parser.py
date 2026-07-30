"""Email parsing and body cleaning utilities."""

import email
import re
from email.header import decode_header
from email.policy import default
from typing import Optional, Tuple
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    """Strip HTML tags and return text."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self) -> str:
        return ''.join(self.text).strip()


def decode_header_value(header: Optional[str]) -> str:
    """Decode RFC 2047 encoded header value to unicode."""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    parts = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                encoding = encoding or "utf-8"
                part = part.decode(encoding, errors="ignore")
            except Exception:
                part = part.decode("utf-8", errors="ignore")
        parts.append(str(part))
    return "".join(parts).strip()


def clean_html(html_text: str) -> str:
    """Remove HTML tags and decode entities."""
    stripper = HTMLStripper()
    stripper.feed(html_text)
    return stripper.get_data()


def extract_plain_text_from_message(msg) -> str:
    """Extract plain text body from email message, with fallback to HTML."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="ignore")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode("utf-8", errors="ignore")
                    return clean_html(html)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="ignore")
    return ""


def clean_email_body(body: str) -> str:
    """Remove quoted replies, signatures, and leading/trailing whitespace.

    This is a basic implementation; can be extended with more heuristics.
    """
    lines = body.splitlines()
    cleaned = []
    quote_pattern = re.compile(r"^>\s*")
    signature_pattern = re.compile(r"^--\s*$")
    skip = False
    for line in lines:
        if signature_pattern.match(line.strip()):
            skip = True
            continue
        if skip:
            continue
        if quote_pattern.match(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


class EmailParser:
    """Parse raw email bytes and extract sender, subject, body, message-id."""

    @staticmethod
    def parse_raw(raw_bytes: bytes) -> dict:
        """Parse raw email bytes and return dict with fields."""
        msg = email.message_from_bytes(raw_bytes, policy=default)
        sender = decode_header_value(msg.get("From", ""))
        subject = decode_header_value(msg.get("Subject", ""))
        body = extract_plain_text_from_message(msg)
        body = clean_email_body(body)
        message_id = msg.get("Message-ID", "").strip()
        # Also get References and In-Reply-To if needed
        in_reply_to = msg.get("In-Reply-To", "").strip()
        references = msg.get("References", "").strip()

        return {
            "sender": sender,
            "subject": subject,
            "body": body,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "raw_msg": msg,
        }
