import pytest

from app.core.config import Settings
from app.core.proxy import via_proxy

SAFE_PRODUCTION = {
    "ENVIRONMENT": "production",
    "DATABASE_URL": "postgresql+asyncpg://u:p@db.example.com:5432/app?ssl=require",
    "DATABASE_URL_SYNC": "postgresql+psycopg://u:p@db.example.com:5432/app?sslmode=require",
    "JWT_SECRET_KEY": "x" * 48,
    "COOKIE_SECURE": True,
    "COOKIE_SAMESITE": "none",
    "BACKEND_CORS_ORIGINS": "https://app.example.com",
}


def test_safe_production_settings_are_accepted():
    assert Settings(_env_file=None, **SAFE_PRODUCTION).is_production


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"JWT_SECRET_KEY": "short"}, "JWT_SECRET_KEY"),
        ({"COOKIE_SECURE": False}, "COOKIE_SECURE"),
        ({"OUTBOUND_PROXY": "http://proxy:80"}, "OUTBOUND_PROXY"),
        ({"BACKEND_CORS_ORIGINS": "http://localhost:5173"}, "BACKEND_CORS_ORIGINS"),
        ({"DATABASE_URL": "postgresql+asyncpg://u:p@127.0.0.1:15432/app?ssl=require"}, "DATABASE_URL"),
        ({"DATABASE_URL": "postgresql+asyncpg://u:p@db.example.com/app"}, "ssl=require"),
        ({"DATABASE_URL_SYNC": "postgresql+psycopg://u:p@db.example.com/app"}, "sslmode=require"),
    ],
)
def test_unsafe_production_settings_are_rejected(override, message):
    with pytest.raises(ValueError, match=message):
        Settings(_env_file=None, **{**SAFE_PRODUCTION, **override})


def test_development_allows_local_settings():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/app",
        DATABASE_URL_SYNC="postgresql+psycopg://u:p@localhost/app",
        JWT_SECRET_KEY="dev",
    )
    assert not settings.is_production


def test_no_proxy_leaves_url_untouched():
    url = "postgresql+asyncpg://u:p%40ss@db.example.com:5432/app"
    assert via_proxy(url, "") == url


def test_proxy_rewrites_url_to_local_tunnel_and_keeps_credentials():
    rewritten = via_proxy("postgresql+psycopg://u:p%40ss@db.example.com:5432/app", "http://proxy:80")
    assert rewritten.startswith("postgresql+psycopg://u:p%40ss@127.0.0.1:")
    assert rewritten.endswith("/app")
    # The same database host reuses one tunnel.
    assert via_proxy("postgresql+psycopg://u:p%40ss@db.example.com:5432/app", "http://proxy:80") == rewritten
