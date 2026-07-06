"""POST /ocr — multipart upload in, recognized text out.

Accepts a scanned notice as an image (PNG / JPEG / WebP) or a PDF:

    curl -F "file=@notice.png" -F "lang=en" .../ocr

Returns:

    {"text": "...", "lang": "en", "engine": "tesseract",
     "pages": [{"page": 1, "text": "...", "source": "ocr"}]}

``source`` is "text-layer" for born-digital PDF pages (no OCR needed),
"ocr" for genuinely scanned content, "mock" from the fallback engine.
Media type is sniffed from magic bytes — the client's Content-Type is
not trusted. Reached through the gateway at /translate/ocr.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["ocr"])


class OcrPageOut(BaseModel):
    page: int
    text: str
    source: str
    image: str | None = None  # JPEG data URL page preview (PDFs)


class OcrResponse(BaseModel):
    text: str
    lang: str
    engine: str
    pages: list[OcrPageOut]


def _sniff_media_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.post("/ocr", response_model=OcrResponse)
async def ocr(
    request: Request,
    file: UploadFile = File(...),
    lang: str = Form(default="auto"),
) -> OcrResponse:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )
    if len(data) > settings.ocr_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.ocr_max_bytes} bytes",
        )
    media_type = _sniff_media_type(data)
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type — send PNG, JPEG, WebP or PDF",
        )
    try:
        result = await request.app.state.ocr_engine.recognize(
            data, media_type=media_type, lang=lang
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return OcrResponse(
        text=result.text,
        lang=result.lang,
        engine=result.engine,
        pages=[
            OcrPageOut(page=p.page, text=p.text, source=p.source, image=p.image)
            for p in result.pages
        ],
    )
