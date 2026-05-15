# LifeBot Media Server

Small FastAPI service for hosting LifeBot `.m4a` audio files and `.png/.jpg` images so LINE can fetch them as audio and image messages.

## Zeabur

Deploy this folder as a Python service.

Environment variables:

```bash
MEDIA_DIR=/data/audio
ARCHIVE_DIR=/data/archive
UPLOAD_TOKEN=choose-a-long-random-token
PUBLIC_BASE_URL=https://your-zeabur-domain.zeabur.app
```

`AUDIO_DIR` is still accepted for backward compatibility when `MEDIA_DIR` is not set.

Add a Zeabur Volume mounted at:

```bash
/data
```

Endpoints:

- `POST /upload/{filename}.m4a` with header `X-Upload-Token`
- `POST /upload/{filename}.png` with header `X-Upload-Token`
- `POST /upload/{filename}.jpg` with header `X-Upload-Token`
- `GET /audio/{filename}.m4a`
- `GET /image/{filename}.png`
- `GET /image/{filename}.jpg`
- `POST /archive/upload/index.html` with header `X-Upload-Token`
- `POST /archive/upload/search.json` with header `X-Upload-Token`
- `POST /archive/upload/posts.jsonl` with header `X-Upload-Token`
- `POST /archive/upload/posts/{post_id}.json` with header `X-Upload-Token`
- `GET /archive/`
- `GET /archive/search.json`
- `GET /archive/posts.jsonl`
- `GET /archive/posts/{post_id}.json`

After deployment, configure Hermes:

```bash
LIFEBOT_AUDIO_UPLOAD_URL=https://your-zeabur-domain.zeabur.app/upload
LIFEBOT_AUDIO_UPLOAD_TOKEN=the-same-token
LIFEBOT_AUDIO_BASE_URL=https://your-zeabur-domain.zeabur.app/audio
LIFEBOT_IMAGE_UPLOAD_URL=https://your-zeabur-domain.zeabur.app/upload
LIFEBOT_IMAGE_UPLOAD_TOKEN=the-same-token
LIFEBOT_IMAGE_BASE_URL=https://your-zeabur-domain.zeabur.app/image
LINE_ARCHIVE_UPLOAD_URL=https://your-zeabur-domain.zeabur.app/archive/upload
LINE_ARCHIVE_UPLOAD_TOKEN=the-same-token
LINE_ARCHIVE_PUBLIC_URL=https://your-zeabur-domain.zeabur.app/archive/
```

Use `LINE_ARCHIVE_PUBLIC_URL` as the LINE rich menu or LIFF URL for "歷史文章".
