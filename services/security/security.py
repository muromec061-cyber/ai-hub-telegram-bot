"""Security service — rate limiting, encryption, RBAC checks."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from typing import Any

from cryptography.fernet import Fernet
from jose import jwt
import bcrypt

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("services.security")


class SecurityService:
    def __init__(self):
        s = get_settings()
        self.jwt_secret = s.security.jwt_secret
        self.jwt_algorithm = s.security.jwt_algorithm
        if s.security.encryption_key:
            try:
                self.fernet = Fernet(s.security.encryption_key.encode())
            except Exception:
                self.fernet = None
        else:
            self.fernet = None
        # In-memory rate limit buckets: {user_id: [(ts, count)]}
        self._rate_buckets: dict[int, list[float]] = defaultdict(list)

    def hash_password(self, password: str) -> str:
        # bcrypt has a 72-byte limit; truncate safely
        pw = password.encode("utf-8")[:72]
        return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
        except Exception:
            return False

    def encrypt(self, text: str) -> str | None:
        if not self.fernet:
            return None
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str | None:
        if not self.fernet:
            return None
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception:
            return None

    def create_jwt(self, payload: dict, expires_in: int = 86400) -> str:
        data = payload.copy()
        data["exp"] = int(time.time()) + expires_in
        return jwt.encode(data, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_jwt(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except Exception:
            return None

    def check_rate_limit(self, user_id: int, *, max_per_minute: int = 30) -> bool:
        """Returns True if request is allowed."""
        now = time.time()
        bucket = self._rate_buckets[user_id]
        # Drop entries older than 60s
        bucket = [t for t in bucket if now - t < 60]
        if len(bucket) >= max_per_minute:
            self._rate_buckets[user_id] = bucket
            return False
        bucket.append(now)
        self._rate_buckets[user_id] = bucket
        return True

    @staticmethod
    def generate_api_key(prefix: str = "sk") -> str:
        return f"{prefix}_{secrets.token_urlsafe(32)}"

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        return hmac.compare_digest(a, b)

    @staticmethod
    def sha256(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
