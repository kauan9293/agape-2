import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_csrf
from app.models import User, UserSession
from app.schemas import AdminSetupInput, LoginInput, UserOut
from app.security import DUMMY_PASSWORD_HASH, create_session, find_session, hash_password, token_digest, verify_password

router = APIRouter(prefix="/api/auth", tags=["autenticação"])
limiter = Limiter(key_func=get_remote_address)


def admin_setup_available(db: Session) -> bool:
    return len(settings.admin_setup_token) >= 32 and db.scalar(select(User.id).where(User.role == "admin").limit(1)) is None


@router.get("/csrf")
def csrf(response: Response, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    auth = find_session(db, request.cookies.get(settings.session_cookie_name))
    token = auth[0].csrf_token if auth else secrets.token_urlsafe(32)
    response.set_cookie("agape_csrf", token, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=3600)
    return {"csrf_token": token}


@router.get("/setup-status")
def setup_status(db: Session = Depends(get_db)) -> dict[str, bool]:
    return {"available": admin_setup_available(db)}


@router.post("/setup", response_model=UserOut, status_code=201, dependencies=[Depends(require_csrf)])
@limiter.limit("5/hour")
def setup_admin(request: Request, response: Response, payload: AdminSetupInput, db: Session = Depends(get_db)) -> User:
    if not admin_setup_available(db):
        raise HTTPException(status_code=409, detail="A configuração inicial não está disponível.")
    if not secrets.compare_digest(payload.setup_token.encode("utf-8"), settings.admin_setup_token.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Código de configuração inválido.")
    user = User(email=str(payload.email).lower(), password_hash=hash_password(payload.password), role="admin")
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível criar o acesso administrativo.")
    token, session = create_session(db, user)
    response.set_cookie(settings.session_cookie_name, token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_hours * 3600, path="/")
    response.set_cookie("agape_csrf", session.csrf_token, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_hours * 3600)
    return user


@router.post("/login", response_model=UserOut, dependencies=[Depends(require_csrf)])
@limiter.limit("10/minute")
def login(request: Request, response: Response, payload: LoginInput, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    valid_password = verify_password(payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid_password or user.role != "admin":
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    token, session = create_session(db, user)
    response.set_cookie(settings.session_cookie_name, token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_hours * 3600, path="/")
    response.set_cookie("agape_csrf", session.csrf_token, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_hours * 3600)
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("agape_csrf", path="/")
    response.status_code = 204
    return response