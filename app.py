import os
import re
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response


MEDIA_DIR = Path(os.getenv("MEDIA_DIR", os.getenv("AUDIO_DIR", "/data/audio")))
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

app = FastAPI(title="LifeBot Media Server")


def safe_media_filename(filename: str) -> str:
    name = Path(filename).name
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.(m4a|png|jpg|jpeg)", name, flags=re.I):
        raise HTTPException(status_code=400, detail="filename must be a safe .m4a, .png, .jpg, or .jpeg name")
    return name


def media_type_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".m4a":
        return "audio/x-m4a"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    raise HTTPException(status_code=400, detail="unsupported media type")


def public_path_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".m4a":
        return f"/audio/{filename}"
    return f"/image/{filename}"


def file_kind_for(filename: str) -> str:
    return "audio" if Path(filename).suffix.lower() == ".m4a" else "image"


@app.get("/")
def health():
    return {"ok": True, "service": "lifebot-media-server"}


@app.post("/upload/{filename}")
async def upload_media(filename: str, request: Request, x_upload_token: str = Header(default="")):
    if not UPLOAD_TOKEN:
        raise HTTPException(status_code=500, detail="UPLOAD_TOKEN is not configured")
    if x_upload_token != UPLOAD_TOKEN:
        raise HTTPException(status_code=401, detail="invalid upload token")

    safe_name = safe_media_filename(filename)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(body) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="media file too large")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    target = MEDIA_DIR / safe_name
    target.write_bytes(body)

    public_path = public_path_for(safe_name)
    url = f"{PUBLIC_BASE_URL}{public_path}" if PUBLIC_BASE_URL else public_path
    return {"ok": True, "filename": safe_name, "kind": file_kind_for(safe_name), "url": url}


@app.get("/audio/{filename}")
def get_audio(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() != ".m4a":
        raise HTTPException(status_code=400, detail="audio endpoint only serves .m4a")
    return media_response(safe_name)


@app.head("/audio/{filename}")
def head_audio(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() != ".m4a":
        raise HTTPException(status_code=400, detail="audio endpoint only serves .m4a")
    return media_response(safe_name, head=True)


@app.get("/image/{filename}")
def get_image(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() == ".m4a":
        raise HTTPException(status_code=400, detail="image endpoint only serves images")
    return media_response(safe_name)


@app.head("/image/{filename}")
def head_image(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() == ".m4a":
        raise HTTPException(status_code=400, detail="image endpoint only serves images")
    return media_response(safe_name, head=True)


def media_response(filename: str, head: bool = False):
    path = MEDIA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="media not found")
    size = path.stat().st_size
    data = b"" if head else path.read_bytes()
    return Response(
        content=data,
        media_type=media_type_for(filename),
        headers={
            "Cache-Control": "public, max-age=604800",
            "Content-Length": str(size),
            "Accept-Ranges": "bytes",
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
