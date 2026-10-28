import hmac

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.security import find_session


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = find_session(db, request.cookies.get(settings.session_cookie_name))
    if auth is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")
    return auth[1]


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não autorizado.")
    return user


def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    cookie_token = request.cookies.get("agape_csrf")
    if not cookie_token or not x_csrf_token or not hmac.compare_digest(cookie_token, x_csrf_token):
        raise HTTPException(status_code=403, detail="Verificação de segurança inválida.")
    session_auth = find_session(db, request.cookies.get(settings.session_cookie_name))
    if session_auth and not hmac.compare_digest(session_auth[0].csrf_token, x_csrf_token):
        raise HTTPException(status_code=403, detail="Verificação de segurança inválida.")