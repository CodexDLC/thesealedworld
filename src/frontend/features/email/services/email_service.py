from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader
from loguru import logger

_DEFAULT_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class EmailService:
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        email_from: str,
        templates_dir: Path | None = None,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._email_from = email_from
        tpl_dir = templates_dir or _DEFAULT_TEMPLATES_DIR
        self._jinja = Environment(loader=FileSystemLoader(str(tpl_dir)), autoescape=True)

    def render_template(self, template_name: str, **context: Any) -> str:
        template = self._jinja.get_template(template_name)
        return template.render(**context)

    async def send(
        self,
        *,
        to: str,
        subject: str,
        body_html: str,
    ) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self._email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        logger.info("Sending email to={} subject={!r}", to, subject)
        await aiosmtplib.send(
            msg,
            hostname=self._smtp_host,
            port=self._smtp_port,
            username=self._smtp_user,
            password=self._smtp_password,
            start_tls=True,
        )
        logger.info("Email sent to={}", to)

    async def send_template(
        self,
        *,
        to: str,
        subject: str,
        template: str,
        **context: Any,
    ) -> None:
        html = self.render_template(template, **context)
        await self.send(to=to, subject=subject, body_html=html)
