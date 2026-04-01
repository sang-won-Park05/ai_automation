from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from main import run_pipeline


app = FastAPI(title="AI Briefing Cron")


def verify_cron_secret(authorization: str | None) -> None:
    cron_secret = os.getenv("CRON_SECRET")
    if not cron_secret:
        return

    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
@app.get("/api/cron")
def run_cron(authorization: str | None = Header(default=None)) -> JSONResponse:
    verify_cron_secret(authorization)

    if not os.getenv("DISCORD_WEBHOOK_URL"):
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "DISCORD_WEBHOOK_URL is not configured",
            },
        )

    try:
        result = run_pipeline(dry_run=False)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc),
            },
        )

    status_code = 200 if result.ok else 500
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": result.ok,
            "sent_to_discord": result.sent_to_discord,
            "preview_path": str(result.preview_path),
            "window": result.window_label,
            "message": result.message,
        },
    )
