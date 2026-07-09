import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import models
import security
from database import get_db

SECRET_KEY = os.getenv("LOGJOBS_SECRET_KEY", "dev-secret-change-in-production")
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7 dias
REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30  # 30 dias
RECUPERACAO_SENHA_EXPIRE_SECONDS = 60 * 60  # 1 hora

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def criar_token(usuario_id: int) -> str:
    payload = {"sub": str(usuario_id), "exp": time.time() + ACCESS_TOKEN_EXPIRE_SECONDS}
    return security.encode_jwt(payload, SECRET_KEY)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def criar_refresh_token(db: Session, usuario_id: int) -> str:
    """Gera um refresh token opaco (não é JWT) e guarda só o hash no banco,
    para permitir revogar sessões sem precisar de uma lista de revogação de JWTs."""
    token = secrets.token_urlsafe(48)
    registro = models.RefreshToken(
        usuario_id=usuario_id,
        token_hash=_hash_token(token),
        expira_em=datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_EXPIRE_SECONDS),
    )
    db.add(registro)
    db.commit()
    return token


def rotacionar_refresh_token(db: Session, token: str) -> Optional[tuple[models.Usuario, str]]:
    """Valida um refresh token e, se válido, revoga-o e emite um novo (rotação
    de uso único — se o mesmo token for reaproveitado depois, já estará revogado)."""
    registro = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == _hash_token(token))
        .first()
    )
    if not registro or registro.revogado_em is not None:
        return None

    expira_em = registro.expira_em
    if expira_em.tzinfo is None:
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    if expira_em < datetime.now(timezone.utc):
        return None

    usuario = db.get(models.Usuario, registro.usuario_id)
    if not usuario:
        return None

    registro.revogado_em = datetime.now(timezone.utc)
    novo_token = criar_refresh_token(db, usuario.id)
    return usuario, novo_token


def revogar_refresh_token(db: Session, token: str) -> None:
    registro = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == _hash_token(token))
        .first()
    )
    if registro and registro.revogado_em is None:
        registro.revogado_em = datetime.now(timezone.utc)
        db.commit()


def revogar_todos_refresh_tokens(db: Session, usuario_id: int) -> None:
    """Encerra todas as sessões persistentes do usuário — usado depois de
    redefinir a senha, para que um possível invasor com a senha antiga
    (e um refresh token já emitido) perca o acesso."""
    db.query(models.RefreshToken).filter(
        models.RefreshToken.usuario_id == usuario_id, models.RefreshToken.revogado_em.is_(None)
    ).update({"revogado_em": datetime.now(timezone.utc)})
    db.commit()


def criar_token_recuperacao_senha(db: Session, usuario_id: int) -> str:
    """Token opaco de uso único para o link de 'esqueci minha senha', enviado
    por e-mail. Guardado só como hash, mesmo raciocínio do refresh token."""
    token = secrets.token_urlsafe(32)
    registro = models.TokenRecuperacaoSenha(
        usuario_id=usuario_id,
        token_hash=_hash_token(token),
        expira_em=datetime.now(timezone.utc) + timedelta(seconds=RECUPERACAO_SENHA_EXPIRE_SECONDS),
    )
    db.add(registro)
    db.commit()
    return token


def validar_e_consumir_token_recuperacao(db: Session, token: str) -> Optional[models.Usuario]:
    """Valida o token de recuperação e, se válido, marca como usado (uso
    único) e devolve o usuário — quem chama é responsável por trocar a senha."""
    registro = (
        db.query(models.TokenRecuperacaoSenha)
        .filter(models.TokenRecuperacaoSenha.token_hash == _hash_token(token))
        .first()
    )
    if not registro or registro.usado_em is not None:
        return None

    expira_em = registro.expira_em
    if expira_em.tzinfo is None:
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    if expira_em < datetime.now(timezone.utc):
        return None

    usuario = db.get(models.Usuario, registro.usuario_id)
    if not usuario:
        return None

    registro.usado_em = datetime.now(timezone.utc)
    db.commit()
    return usuario


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
