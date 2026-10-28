import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserSession

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("invalid-login-timing-equalization")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hash.verify(password, encoded)
    except Exception:
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> tuple[str, UserSession]:
    token = secrets.token_urlsafe(48)
    session = UserSession(
        user_id=user.id,
        token_hash=token_digest(token),
        csrf_token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_hours),
    )
    db.add(session)
    db.commit()
    return token, session


def find_session(db: Session, token: str | None) -> tuple[UserSession, User] | None:
    if not token:
        return None
    result = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == token_digest(token))
    ).first()
    if result is None:
        return None
    session, user = result
    expiry = session.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session, user