from dataclasses import dataclass, field
from urllib.parse import parse_qs

from fastapi import Request

from src.frontend.features.auth.dto.user import PASSWORD_MIN_LENGTH


@dataclass
class RegisterForm:
    email: str = ""
    password: str = ""
    password_confirm: str = ""
    referrer_code: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    async def from_request(cls, request: Request) -> "RegisterForm":
        raw_body = (await request.body()).decode("utf-8")
        form_data = parse_qs(raw_body, keep_blank_values=True)
        return cls(
            email=form_data.get("email", [""])[0].strip().lower(),
            password=form_data.get("password", [""])[0],
            password_confirm=form_data.get("password_confirm", [""])[0],
            referrer_code=form_data.get("referrer_code", [""])[0].strip(),
        )

    @property
    def is_valid(self) -> bool:
        self.errors.clear()
        if not self.email or "@" not in self.email or "." not in self.email.rsplit("@", maxsplit=1)[-1]:
            self.errors.append("Valid email is required")
        if len(self.password) < PASSWORD_MIN_LENGTH:
            self.errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        if self.password != self.password_confirm:
            self.errors.append("Passwords do not match")
        local = self.email.split("@", maxsplit=1)[0].lower()
        if local and self.password and local in self.password.lower():
            self.errors.append("Password must not contain the email local part")
        return len(self.errors) == 0
