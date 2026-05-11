# Security

`src/backend/core/security.py` — утилиты аутентификации. JWT делегируется в `features_site/auth`, хеширование паролей живёт здесь.

## Хеширование паролей

PBKDF2-SHA256 с 390 000 итерациями. Формат хранения: `pbkdf2_sha256$<iterations>$<salt_b64>$<digest_b64>`.

```python
hashed = get_password_hash("my_password")
ok = verify_password("my_password", hashed)  # True
```

Сравнение через `hmac.compare_digest` — защита от timing attacks.

## JWT

`create_access_token` / `decode_access_token` — реэкспорт из `features_site/auth/security/token_service`. Документация токенов: см. `backend/features_site/auth`.
