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

`create_access_token` / `decode_access_token` используют AuthX за проектными
обертками. Код роутов и фич должен импортировать проектные зависимости
аутентификации, а не AuthX напрямую.

Текущий baseline:

- access JWT создается и проверяется через AuthX;
- refresh tokens остаются проектными opaque-токенами с хранением в БД;
- хеширование паролей остается в проектном коде;
- browser-cookie flow принадлежит frontend/site слою;
- роли, scopes, revoke/blocklist и CSRF-политика являются отдельным будущим
  расширением security runtime.
