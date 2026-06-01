import os
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response


MEDIA_DIR = Path(os.getenv("MEDIA_DIR", os.getenv("AUDIO_DIR", "/data/audio")))
ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "/data/archive"))
PODCAST_DIR = Path(os.getenv("PODCAST_DIR", "/data/podcast"))
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

app = FastAPI(title="LifeBot Media Server")


def safe_media_filename(filename: str) -> str:
    name = Path(filename).name
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.(m4a|mp3|mp4|png|jpg|jpeg)", name, flags=re.I):
        raise HTTPException(status_code=400, detail="filename must be a safe .m4a, .mp3, .mp4, .png, .jpg, or .jpeg name")
    return name


def media_type_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".mp4":
        return "video/mp4"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    raise HTTPException(status_code=400, detail="unsupported media type")


def public_path_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".m4a", ".mp3"}:
        return f"/audio/{filename}"
    if suffix == ".mp4":
        return f"/video/{filename}"
    return f"/image/{filename}"


def file_kind_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".m4a", ".mp3"}:
        return "audio"
    if suffix == ".mp4":
        return "video"
    return "image"


def safe_archive_path(path: str) -> Path:
    clean = Path(path)
    if clean.is_absolute() or ".." in clean.parts:
        raise HTTPException(status_code=400, detail="archive path must be relative")
    if len(clean.parts) > 2:
        raise HTTPException(status_code=400, detail="archive path is too deep")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+\.(html|json|jsonl)", path, flags=re.I):
        raise HTTPException(status_code=400, detail="archive file must be .html, .json, or .jsonl")
    if len(clean.parts) == 2 and clean.parts[0] != "posts":
        raise HTTPException(status_code=400, detail="only posts/ subdirectory is supported")
    return clean


def archive_media_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix in {".json", ".jsonl"}:
        return "application/json; charset=utf-8"
    raise HTTPException(status_code=400, detail="unsupported archive type")


def safe_podcast_path(path: str) -> Path:
    clean = Path(path)
    if clean.is_absolute() or ".." in clean.parts:
        raise HTTPException(status_code=400, detail="podcast path must be relative")
    if len(clean.parts) > 2:
        raise HTTPException(status_code=400, detail="podcast path is too deep")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+\.(xml|json)", path, flags=re.I):
        raise HTTPException(status_code=400, detail="podcast file must be .xml or .json")
    if len(clean.parts) == 2 and clean.parts[0] != "episodes":
        raise HTTPException(status_code=400, detail="only episodes/ subdirectory is supported")
    return clean


def podcast_media_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".xml":
        return "application/rss+xml; charset=utf-8"
    if suffix == ".json":
        return "application/json; charset=utf-8"
    raise HTTPException(status_code=400, detail="unsupported podcast type")


@app.get("/")
def health():
    return {"ok": True, "service": "lifebot-media-server", "archive": "/archive/", "podcast": "/podcast/feed.xml"}


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
    if len(body) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="media file too large")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    target = MEDIA_DIR / safe_name
    target.write_bytes(body)

    public_path = public_path_for(safe_name)
    url = f"{PUBLIC_BASE_URL}{public_path}" if PUBLIC_BASE_URL else public_path
    return {"ok": True, "filename": safe_name, "kind": file_kind_for(safe_name), "url": url}


@app.post("/podcast/upload/{path:path}")
async def upload_podcast_file(path: str, request: Request, x_upload_token: str = Header(default="")):
    if not UPLOAD_TOKEN:
        raise HTTPException(status_code=500, detail="UPLOAD_TOKEN is not configured")
    if x_upload_token != UPLOAD_TOKEN:
        raise HTTPException(status_code=401, detail="invalid upload token")

    safe_path = safe_podcast_path(path)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="podcast file too large")

    target = PODCAST_DIR / safe_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)

    public_path = f"/podcast/{safe_path.as_posix()}"
    url = f"{PUBLIC_BASE_URL}{public_path}" if PUBLIC_BASE_URL else public_path
    return {"ok": True, "path": safe_path.as_posix(), "kind": "podcast", "url": url}


@app.post("/archive/upload/{path:path}")
async def upload_archive_file(path: str, request: Request, x_upload_token: str = Header(default="")):
    if not UPLOAD_TOKEN:
        raise HTTPException(status_code=500, detail="UPLOAD_TOKEN is not configured")
    if x_upload_token != UPLOAD_TOKEN:
        raise HTTPException(status_code=401, detail="invalid upload token")

    safe_path = safe_archive_path(path)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(body) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="archive file too large")

    target = ARCHIVE_DIR / safe_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)

    public_path = f"/archive/{safe_path.as_posix()}"
    url = f"{PUBLIC_BASE_URL}{public_path}" if PUBLIC_BASE_URL else public_path
    return {"ok": True, "path": safe_path.as_posix(), "kind": "archive", "url": url}


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
    if Path(safe_name).suffix.lower() in {".m4a", ".mp3", ".mp4"}:
        raise HTTPException(status_code=400, detail="image endpoint only serves images")
    return media_response(safe_name)


@app.head("/image/{filename}")
def head_image(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() in {".m4a", ".mp3", ".mp4"}:
        raise HTTPException(status_code=400, detail="image endpoint only serves images")
    return media_response(safe_name, head=True)


@app.get("/video/{filename}")
def get_video(filename: str, range_header: str = Header(default="", alias="Range")):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() != ".mp4":
        raise HTTPException(status_code=400, detail="video endpoint only serves .mp4")
    return media_response(safe_name, range_header=range_header)


@app.head("/video/{filename}")
def head_video(filename: str):
    safe_name = safe_media_filename(filename)
    if Path(safe_name).suffix.lower() != ".mp4":
        raise HTTPException(status_code=400, detail="video endpoint only serves .mp4")
    return media_response(safe_name, head=True)


@app.get("/archive")
def get_archive_redirect():
    return archive_response("index.html")


@app.get("/archive/")
def get_archive_index():
    return archive_response("index.html")


@app.get("/archive/{path:path}")
def get_archive_file(path: str):
    return archive_response(path)


@app.get("/podcast")
def get_podcast_feed_redirect():
    return podcast_response("feed.xml")


@app.head("/podcast")
def head_podcast_feed_redirect():
    return podcast_response("feed.xml", head=True)


@app.get("/podcast/")
def get_podcast_feed_index():
    return podcast_response("feed.xml")


@app.head("/podcast/")
def head_podcast_feed_index():
    return podcast_response("feed.xml", head=True)


@app.get("/podcast/{path:path}")
def get_podcast_file(path: str):
    return podcast_response(path)


@app.head("/podcast/{path:path}")
def head_podcast_file(path: str):
    return podcast_response(path, head=True)


def archive_response(path: str):
    safe_path = safe_archive_path(path)
    file_path = ARCHIVE_DIR / safe_path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="archive file not found")
    return Response(
        content=file_path.read_bytes(),
        media_type=archive_media_type(safe_path.name),
        headers={"Cache-Control": "public, max-age=300"},
    )


def podcast_response(path: str, head: bool = False):
    safe_path = safe_podcast_path(path)
    file_path = PODCAST_DIR / safe_path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="podcast file not found")
    data = b"" if head else file_path.read_bytes()
    return Response(
        content=data,
        media_type=podcast_media_type(safe_path.name),
        headers={"Cache-Control": "public, max-age=300", "Content-Length": str(file_path.stat().st_size)},
    )


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
