# LifeBot Audio Server

Small FastAPI service for hosting LifeBot `.m4a` audio files so LINE can fetch them as audio messages.

## Zeabur

Deploy this folder as a Python service.

Environment variables:

```bash
AUDIO_DIR=/data/audio
UPLOAD_TOKEN=choose-a-long-random-token
PUBLIC_BASE_URL=https://your-zeabur-domain.zeabur.app
```

Add a Zeabur Volume mounted at:

```bash
/data
```

Endpoints:

- `POST /upload/{filename}.m4a` with header `X-Upload-Token`
- `GET /audio/{filename}.m4a`

After deployment, configure Hermes:

```bash
LIFEBOT_AUDIO_UPLOAD_URL=https://your-zeabur-domain.zeabur.app/upload
LIFEBOT_AUDIO_UPLOAD_TOKEN=the-same-token
LIFEBOT_AUDIO_BASE_URL=https://your-zeabur-domain.zeabur.app/audio
```
