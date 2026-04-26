import os
import re
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse


AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "/data/audio"))
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

app = FastAPI(title="LifeBot Audio Server")


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.m4a", name):
        raise HTTPException(status_code=400, detail="filename must be a safe .m4a name")
    return name


@app.get("/")
def health():
    return {"ok": True, "service": "lifebot-audio-server"}


@app.post("/upload/{filename}")
async def upload_audio(filename: str, request: Request, x_upload_token: str = Header(default="")):
    if not UPLOAD_TOKEN:
        raise HTTPException(status_code=500, detail="UPLOAD_TOKEN is not configured")
    if x_upload_token != UPLOAD_TOKEN:
        raise HTTPException(status_code=401, detail="invalid upload token")

    safe_name = safe_filename(filename)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(body) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="audio file too large")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    target = AUDIO_DIR / safe_name
    target.write_bytes(body)

    url = f"{PUBLIC_BASE_URL}/audio/{safe_name}" if PUBLIC_BASE_URL else f"/audio/{safe_name}"
    return {"ok": True, "filename": safe_name, "url": url}


@app.get("/audio/{filename}")
def get_audio(filename: str):
    safe_name = safe_filename(filename)
    path = AUDIO_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(
        path,
        media_type="audio/mp4",
        filename=safe_name,
        headers={"Cache-Control": "public, max-age=604800"},
    )


@app.head("/audio/{filename}")
def head_audio(filename: str):
    safe_name = safe_filename(filename)
    path = AUDIO_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(
        path,
        media_type="audio/mp4",
        filename=safe_name,
        headers={"Cache-Control": "public, max-age=604800"},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
