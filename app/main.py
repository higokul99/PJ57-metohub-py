from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.routers import admin, platform, storefront

app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, same_site="lax", https_only=False)

(BASE_DIR / "uploads" / "stores").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")

app.include_router(platform.router)
app.include_router(storefront.router)
app.include_router(admin.router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health")
def health():
    return JSONResponse({"ok": True, "app": settings.APP_NAME})
