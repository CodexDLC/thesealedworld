from unittest.mock import AsyncMock, patch

import pytest

from src.frontend.features.email.services.email_service import EmailService


@pytest.mark.unit
class TestEmailService:
    @pytest.fixture
    def service(self):
        return EmailService(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="secret",
            email_from="noreply@thesealed.world",
            templates_dir=None,
        )

    @pytest.mark.asyncio
    @patch("src.frontend.features.email.services.email_service.aiosmtplib")
    async def test_send_renders_template_and_calls_smtp(self, mock_smtp, service):
        mock_smtp.send = AsyncMock()

        await service.send(
            to="player@example.com",
            subject="Welcome",
            body_html="<h1>Hello</h1>",
        )

        mock_smtp.send.assert_awaited_once()
        call_args = mock_smtp.send.call_args
        message = call_args[0][0]
        assert "player@example.com" in message["To"]
        assert message["Subject"] == "Welcome"

    @pytest.mark.asyncio
    @patch("src.frontend.features.email.services.email_service.aiosmtplib")
    async def test_send_formats_from_address(self, mock_smtp, service):
        mock_smtp.send = AsyncMock()

        await service.send(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )

        call_args = mock_smtp.send.call_args
        message = call_args[0][0]
        assert message["From"] == "noreply@thesealed.world"

    @pytest.mark.asyncio
    @patch("src.frontend.features.email.services.email_service.aiosmtplib")
    async def test_send_uses_correct_smtp_settings(self, mock_smtp, service):
        mock_smtp.send = AsyncMock()

        await service.send(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )

        call_kwargs = mock_smtp.send.call_args[1]
        assert call_kwargs["hostname"] == "smtp.test.com"
        assert call_kwargs["port"] == 587
        assert call_kwargs["username"] == "test@test.com"
        assert call_kwargs["password"] == "secret"
        assert call_kwargs["start_tls"] is True


@pytest.mark.unit
class TestEmailTemplates:
    @pytest.fixture
    def service(self):
        from pathlib import Path
        templates_dir = Path(__file__).parent.parent.parent.parent.parent / "src" / "frontend" / "features" / "email" / "templates"
        return EmailService(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="",
            email_from="noreply@thesealed.world",
            templates_dir=templates_dir,
        )

    def test_applicant_received_template_renders(self, service):
        html = service.render_template("applicant_received.html", email="player@test.com")
        assert "player@test.com" in html

    def test_tester_approved_template_renders(self, service):
        html = service.render_template("tester_approved.html", email="player@test.com")
        assert "player@test.com" in html

    def test_admin_new_applicant_template_contains_email(self, service):
        html = service.render_template("admin_new_applicant.html", email="newbie@test.com")
        assert "newbie@test.com" in html

    def test_tester_denied_template_renders(self, service):
        html = service.render_template("tester_denied.html", email="denied@test.com")
        assert "denied@test.com" in html
