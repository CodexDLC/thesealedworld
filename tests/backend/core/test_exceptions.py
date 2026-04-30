import pytest
import json
from fastapi import Request
from src.backend.core.exceptions import (
    BaseAPIException,
    AuthException,
    BusinessLogicException,
    api_exception_handler
)

@pytest.mark.unit
class TestExceptions:
    def test_base_api_exception(self):
        exc = BaseAPIException(status_code=400, detail="Error", error_code="custom_code", extra={"foo": "bar"})
        assert exc.status_code == 400
        assert exc.detail == "Error"
        assert exc.error_code == "custom_code"
        assert exc.extra == {"foo": "bar"}

    def test_auth_exception(self):
        exc = AuthException(detail="Failed")
        assert exc.status_code == 401
        assert exc.error_code == "auth_error"
        assert exc.extra["headers"]["WWW-Authenticate"] == "Bearer"

    def test_business_logic_exception(self):
        exc = BusinessLogicException(detail="Conflict")
        assert exc.status_code == 409
        assert exc.error_code == "business_conflict"
        assert exc.detail == "Conflict"

    @pytest.mark.asyncio
    async def test_api_exception_handler(self, mocker):
        mock_request = mocker.MagicMock(spec=Request)
        exc = BaseAPIException(
            status_code=403,
            detail="Forbidden",
            error_code="forbidden",
            extra={"meta": "data", "headers": {"X-Test": "Val"}}
        )

        response = await api_exception_handler(mock_request, exc)

        assert response.status_code == 403
        data = json.loads(response.body.decode())
        assert data["error"]["code"] == "forbidden"
        assert data["error"]["message"] == "Forbidden"
        assert data["error"]["meta"] == "data"
        assert response.headers["X-Test"] == "Val"
