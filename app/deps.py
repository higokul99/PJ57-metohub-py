from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Tenant, User
from app.security import csrf_token


def login_user(request: Request, user: User, tenant: Tenant | None = None) -> None:
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_email"] = user.email
    request.session["user_role"] = user.role
    if tenant:
        request.session["tenant_id"] = tenant.id
        request.session["tenant_slug"] = tenant.slug
        request.session["tenant_name"] = tenant.name
        request.session["tenant_currency"] = tenant.currency or "₹"
    else:
        for key in ("tenant_id", "tenant_slug", "tenant_name", "tenant_currency"):
            request.session.pop(key, None)


def logout_user(request: Request) -> None:
    request.session.clear()


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def current_tenant(request: Request, db: Session = Depends(get_db)) -> Tenant | None:
    user_id = request.session.get("user_id")
    tenant_id = request.session.get("tenant_id")
    if tenant_id:
        tenant = (
            db.query(Tenant)
            .options(joinedload(Tenant.plan))
            .filter(Tenant.id == tenant_id)
            .first()
        )
        if tenant:
            return tenant
    if user_id:
        tenant = (
            db.query(Tenant)
            .options(joinedload(Tenant.plan))
            .filter(Tenant.user_id == user_id)
            .first()
        )
        if tenant:
            request.session["tenant_id"] = tenant.id
            request.session["tenant_slug"] = tenant.slug
            request.session["tenant_name"] = tenant.name
            return tenant
    return None


def require_seller(request: Request, db: Session = Depends(get_db)) -> tuple[User, Tenant]:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    tenant = current_tenant(request, db)
    if not tenant and user.role != "admin":
        raise HTTPException(status_code=302, headers={"Location": "/register"})
    if not tenant:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user, tenant


def template_globals(request: Request) -> dict:
    return {
        "request": request,
        "csrf_token": csrf_token(request),
        "user_name": request.session.get("user_name"),
        "user_id": request.session.get("user_id"),
        "tenant_name": request.session.get("tenant_name"),
        "tenant_slug": request.session.get("tenant_slug"),
    }


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(url=path, status_code=303)
