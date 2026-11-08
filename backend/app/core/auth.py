from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

from app.core.settings import settings

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    def __init__(self, user_id: str, email: str | None = None):
        self.id = user_id
        self.email = email


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured.")
    return PyJWKClient(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid Supabase access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not settings.supabase_url:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["ES256", "RS256", "EdDSA"],
            audience=settings.supabase_jwt_audience,
            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise unauthorized
        return AuthenticatedUser(user_id=user_id, email=claims.get("email"))
    except HTTPException:
        raise
    except (jwt.PyJWTError, PyJWKClientError, RuntimeError, ValueError):
        raise unauthorized


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
