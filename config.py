"""Pydantic settings with validation and environment defaults."""

from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    email_address: str = Field(..., env="EMAIL_ADDRESS")
    email_app_password: str = Field(..., env="EMAIL_APP_PASSWORD")
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    llm_model: str = Field("llama-3.3-70b-versatile", env="LLM_MODEL")
    check_interval: int = Field(60, env="CHECK_INTERVAL", gt=0)

    imap_server: str = Field("imap.gmail.com", env="IMAP_SERVER")
    imap_port: int = Field(993, env="IMAP_PORT", gt=0)
    smtp_server: str = Field("smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(587, env="SMTP_PORT", gt=0)

    log_dir: str = Field("logs", env="LOG_DIR")
    llm_retries: int = Field(3, env="LLM_RETRIES", ge=1)
    retry_base_seconds: int = Field(1, env="RETRY_BASE_SECONDS", ge=1)

    relevance_keywords: List[str] = Field(
        default=[
            "stok", "ketersediaan", "produk", "barang", "harga", "beli", "order",
            "pemesanan", "tersedia", "ready", "stock", "availability", "price",
            "purchase", "produk", "persediaan"
        ],
        env="RELEVANCE_KEYWORDS"
    )
    ignore_senders: List[str] = Field(
        default=[
            "no-reply", "noreply", "mailer-daemon", "postmaster", "newsletter",
            "notifications", "alert", "security", "verification"
        ],
        env="IGNORE_SENDERS"
    )
    ignore_domains: List[str] = Field(
        default=[
            "google.com", "googlemail.com", "accounts.google.com",
            "amazon.com", "paypal.com", "facebook.com", "instagram.com",
            "twitter.com", "x.com", "shopify.com", "mailchimp.com"
        ],
        env="IGNORE_DOMAINS"
    )
    fallback_reply_template: str = Field(
        default="""Yth. Customer,

Terima kasih atas email Anda.

Untuk pertanyaan tentang stok, harga, atau pemesanan produk, silakan kirim email ke alamat ini.
Untuk pertanyaan lain atau bantuan teknis, silakan hubungi tim support kami di support@perusahaan.com atau kunjungi website kami di https://www.perusahaan.com/help.

Kami siap membantu Anda.

Hormat kami,
Tim Customer Service""",
        env="FALLBACK_REPLY_TEMPLATE"
    )
    processed_storage_file: str = Field(
        "outputs/processed_emails.json",
        env="PROCESSED_STORAGE_FILE"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("EMAIL_ADDRESS must contain '@'")
        return v

    @model_validator(mode="after")
    def check_smtp_port(self) -> "Settings":
        # If needed, can add validation for SMTP port (e.g., only 465 or 587)
        # For flexibility, we allow any port but warn if not typical.
        if self.smtp_port not in (465, 587):
            # Optionally log a warning, but we cannot access logger here.
            # We'll just accept it.
            pass
        return self
