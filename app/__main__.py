"""CLI entrypoint: `python -m app` or the `aisb` script."""

import uvicorn

from app.config.settings import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )


if __name__ == "__main__":
    run()
