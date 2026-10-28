from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers import admin, auth, public


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Confeitaria Ágape Artesanal", version="1.0.0", lifespan=lifespan)
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(admin.router)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.upload_dir), name="media")
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    class SPAStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            try:
                return await super().get_response(path, scope)
            except HTTPException as error:
                if error.status_code != 404 or path.startswith("api/"):
                    raise
                return await super().get_response("index.html", scope)

    app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="frontend")


@app.get("/api/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}