import os
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response


MEDIA_DIR = Path(os.getenv("MEDIA_DIR", os.getenv("AUDIO_DIR", "/data/audio")))
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

app = FastAPI(title="LifeBot Media Server")


def safe_media_filename(filename: str) -> str:
    name = Path(filename).name
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.(m4a|mp3|png|jpg|jpeg)", name, flags=re.I):
        raise HTTPException(status_code=400, detail="filename must be a safe .m4a, .mp3, .png, .jpg, or .jpeg name")
    return name


def media_type_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    raise HTTPException(status_code=400, detail="unsupported media type")


def public_path_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".m4a", ".mp3"}:
        return f"/audio/{filename}"
    return f"/image/{filename}"


def file_kind_for(filename: str) -> str:
    return "audio" if Path(filename).suffix.lower() in {".m4a", ".mp3"} else "image"


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
def get_audio(filename: str, range_header: str = Header(default="", alias="Range")):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() not in {".m4a", ".mp3"}:
        raise HTTPException(status_code=400, detail="audio endpoint only serves .m4a and .mp3")
    return media_response(safe_name, range_header=range_header)


@app.head("/audio/{filename}")
def head_audio(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() not in {".m4a", ".mp3"}:
        raise HTTPException(status_code=400, detail="audio endpoint only serves .m4a and .mp3")
    return media_response(safe_name, head=True)


@app.get("/image/{filename}")
def get_image(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() in {".m4a", ".mp3"}:
        raise HTTPException(status_code=400, detail="image endpoint only serves images")
    return media_response(safe_name)


@app.head("/image/{filename}")
def head_image(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() in {".m4a", ".mp3"}:
        raise HTTPException(status_code=400, detail="image endpoint only serves images")
    return media_response(safe_name, head=True)


def parse_range_header(range_header: str, size: int) -> Optional[tuple[int, int]]:
    if not range_header:
        return None
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not match:
        raise HTTPException(status_code=416, detail="invalid range")

    start_raw, end_raw = match.groups()
    if not start_raw and not end_raw:
        raise HTTPException(status_code=416, detail="invalid range")

    if start_raw:
        start = int(start_raw)
        end = int(end_raw) if end_raw else size - 1
    else:
        suffix_length = int(end_raw)
        if suffix_length <= 0:
            raise HTTPException(status_code=416, detail="invalid range")
        start = max(size - suffix_length, 0)
        end = size - 1

    if start >= size or end < start:
        raise HTTPException(status_code=416, detail="range not satisfiable")
    return start, min(end, size - 1)


def media_response(filename: str, head: bool = False, range_header: str = ""):
    path = MEDIA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="media not found")
    size = path.stat().st_size
    requested_range = None if head else parse_range_header(range_header, size)
    status_code = 200
    headers = {
        "Cache-Control": "public, max-age=604800",
        "Accept-Ranges": "bytes",
        "Content-Length": str(size),
    }

    if requested_range:
        start, end = requested_range
        status_code = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(end - start + 1)
        with path.open("rb") as file:
            file.seek(start)
            data = file.read(end - start + 1)
    else:
        data = b"" if head else path.read_bytes()

    return Response(
        content=data,
        status_code=status_code,
        media_type=media_type_for(filename),
        headers=headers,
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
