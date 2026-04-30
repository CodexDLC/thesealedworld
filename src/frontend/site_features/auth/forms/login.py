from dataclasses import dataclass
from urllib.parse import parse_qs

from fastapi import Request


@dataclass
class LoginForm:
    email: str = ""
    password: str = ""
    error: str | None = None

    @classmethod
    async def from_request(cls, request: Request) -> "LoginForm":
        raw_body = (await request.body()).decode("utf-8")
        form_data = parse_qs(raw_body, keep_blank_values=True)
        return cls(
            email=form_data.get("email", [""])[0].strip().lower(),
            password=form_data.get("password", [""])[0],
        )

    @property
    def is_valid(self) -> bool:
        if not self.email or not self.password:
            self.error = "Email and password are required"
            return False
        return True
