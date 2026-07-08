import os
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import models
import security
from database import get_db

SECRET_KEY = os.getenv("LOGJOBS_SECRET_KEY", "dev-secret-change-in-production")
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7 dias

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def criar_token(usuario_id: int) -> str:
    payload = {"sub": str(usuario_id), "exp": time.time() + ACCESS_TOKEN_EXPIRE_SECONDS}
    return security.encode_jwt(payload, SECRET_KEY)


def usuario_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.Usuario:
    erro_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise erro_credenciais

    payload = security.decode_jwt(token, SECRET_KEY)
    if not payload:
        raise erro_credenciais

    try:
        usuario_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise erro_credenciais

    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise erro_credenciais
    return usuario


def usuario_atual_opcional(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    if not token:
        return None
    payload = security.decode_jwt(token, SECRET_KEY)
    if not payload:
        return None
    try:
        usuario_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    return db.get(models.Usuario, usuario_id)
