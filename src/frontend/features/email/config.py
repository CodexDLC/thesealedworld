from src.frontend.config.settings import settings
from src.frontend.features.email.services.email_service import EmailService


def get_email_service() -> EmailService:
    return EmailService(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_start_tls=settings.smtp_start_tls,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        email_from=settings.email_from,
    )
