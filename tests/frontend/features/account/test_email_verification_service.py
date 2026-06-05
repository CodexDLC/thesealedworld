import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.account.services.email_verification_service import (
    PURPOSE_CHANGE,
    PURPOSE_VERIFY,
    EmailVerificationService,
)
from src.shared.exceptions import AuthException, BusinessLogicException


@pytest.fixture
def session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def users():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_email = AsyncMock()
    return repo


@pytest.fixture
def tokens():
    repo = MagicMock()
    repo.delete_all_for_user = AsyncMock()
    return repo


@pytest.fixture
def email():
    svc = MagicMock()
    svc.send_template = AsyncMock()
    return svc


@pytest.fixture
def service(session, users, tokens, email):
    return EmailVerificationService(
        session=session,
        users=users,
        tokens=tokens,
        email_service=email,
        site_base_url="https://example.test",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_verify_current_sends_email_with_token_link(service, session, email):
    user = MagicMock(id=uuid.uuid4(), email="user@example.com")
    await service.start_verify_current(user)
    session.add.assert_called_once()
    issued_row = session.add.call_args.args[0]
    assert issued_row.purpose == PURPOSE_VERIFY
    assert issued_row.new_email is None
    assert len(issued_row.token_hash) == 64
    email.send_template.assert_awaited_once()
    kwargs = email.send_template.await_args.kwargs
    assert kwargs["to"] == "user@example.com"
    assert kwargs["template"] == "email_verify_current.html"
    assert kwargs["link"].startswith("https://example.test/account/email/verify/")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_change_email_rejects_wrong_password(service, users, mocker):
    mocker.patch(
        "src.frontend.features.account.services.email_verification_service.verify_password",
        return_value=False,
    )
    user = MagicMock(hashed_password="x")
    with pytest.raises(AuthException):
        await service.start_change_email(user, "new@example.com", "wrong")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_change_email_rejects_existing_email(service, users, mocker):
    mocker.patch(
        "src.frontend.features.account.services.email_verification_service.verify_password",
        return_value=True,
    )
    user = MagicMock(hashed_password="x", id=uuid.uuid4())
    users.get_by_email = AsyncMock(return_value=MagicMock(id=uuid.uuid4()))
    with pytest.raises(BusinessLogicException):
        await service.start_change_email(user, "taken@example.com", "ok")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_verify_success_writes_email_verified_at(service, session, users):
    plain = "plain-token"
    token_hash = hashlib.sha256(plain.encode()).hexdigest()
    user_id = uuid.uuid4()
    row = MagicMock(
        id=1,
        user_id=user_id,
        purpose=PURPOSE_VERIFY,
        new_email=None,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        consumed_at=None,
    )
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=select_result)
    users.get_by_id = AsyncMock(return_value=MagicMock(id=user_id, email="u@e.com"))

    refreshed = await service.consume(plain, PURPOSE_VERIFY)
    assert refreshed is not None
    # consumed and verified updates issued
    assert session.execute.await_count >= 3  # lookup + verified update + consumed update


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_rejects_expired_token(service, session):
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = MagicMock(
        consumed_at=None,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    session.execute = AsyncMock(return_value=select_result)
    with pytest.raises(BusinessLogicException):
        await service.consume("plain", PURPOSE_VERIFY)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_change_email_invalidates_refresh_tokens(service, session, users, tokens):
    plain = "plain-token"
    user_id = uuid.uuid4()
    row = MagicMock(
        id=2,
        user_id=user_id,
        purpose=PURPOSE_CHANGE,
        new_email="new@example.com",
        token_hash=hashlib.sha256(plain.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        consumed_at=None,
    )
    lookup_result = MagicMock()
    lookup_result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=lookup_result)
    users.get_by_id = AsyncMock(return_value=MagicMock(id=user_id, email="old@example.com"))
    users.get_by_email = AsyncMock(return_value=None)

    await service.consume(plain, PURPOSE_CHANGE)
    tokens.delete_all_for_user.assert_awaited_once_with(user_id)
