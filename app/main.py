from fastapi import FastAPI

from app.api.webhooks import router as webhook_router


app = FastAPI(
    title="CyArt DarkTrace User Alerting API",
    version="1.0.0",
)


app.include_router(webhook_router)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
    }
