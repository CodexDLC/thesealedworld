from dataclasses import dataclass, field
from urllib.parse import parse_qs

from fastapi import Request


@dataclass
class RegisterForm:
    email: str = ""
    password: str = ""
    password_confirm: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    async def from_request(cls, request: Request) -> "RegisterForm":
        raw_body = (await request.body()).decode("utf-8")
        form_data = parse_qs(raw_body, keep_blank_values=True)
        return cls(
            email=form_data.get("email", [""])[0].strip().lower(),
            password=form_data.get("password", [""])[0],
            password_confirm=form_data.get("password_confirm", [""])[0],
        )

    @property
    def is_valid(self) -> bool:
        self.errors.clear()
        if not self.email or "@" not in self.email:
            self.errors.append("Valid email is required")
        if len(self.password) < 8:
            self.errors.append("Password must be at least 8 characters")
        if self.password != self.password_confirm:
            self.errors.append("Passwords do not match")
        return len(self.errors) == 0
