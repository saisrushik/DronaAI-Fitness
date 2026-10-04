from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.api.router import api_router
from app.core.config import settings
from app.core.rate_limit import limiter

# The interactive docs map the whole API surface, so they stay off in production.
docs_url = None if settings.is_production else "/docs"

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=docs_url,
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# The largest legitimate payload (a full week of meal changes) is a few kilobytes.
MAX_BODY_BYTES = 256 * 1024


@app.middleware("http")
async def guard_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # The session cookie is SameSite=None, so browsers attach it to cross-site requests too.
    # Rejecting writes from unknown origins stops other sites acting as the signed-in user.
    origin = request.headers.get("origin")
    if request.method not in SAFE_METHODS and origin and origin not in settings.cors_origins:
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)

    content_length = request.headers.get("content-length", "")
    if content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request body too large"}, status_code=413)

    return await call_next(request)


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.PROJECT_NAME, "status": "ok"}
