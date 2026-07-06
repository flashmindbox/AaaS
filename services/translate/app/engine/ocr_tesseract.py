"""Tesseract-backed OCR for scanned notices (images + PDFs).

Classic CPU OCR — no torch, no GPU, milliseconds-to-seconds per page —
chosen deliberately over Surya/EasyOCR for the demo footprint. Odia
support comes from the ``ori`` traineddata fetched by
``bundle/prefetch_tessdata.py`` into ``models/tessdata`` (passed via
``--tessdata-dir`` so nothing touches the system install).

PDFs: born-digital pages already carry a text layer — extracting it is
both faster and more accurate than OCR, so each page tries the text
layer first and only rasterizes + OCRs pages that are genuinely scans.

All third-party imports (pytesseract / pypdfium2 / PIL) happen inside
methods: the ``[ocr]`` extra is optional, and the PyInstaller bundle
build imports every ``app`` submodule during analysis — a module-level
import would break lean builds. When anything is missing, ``load()``
raises and the app factory swaps in the mock engine (same pattern as
the STT service).
"""

from __future__ import annotations

import asyncio
import io
import shutil
from pathlib import Path

import structlog

from app.engine.ocr_base import OcrPage, OcrResult

logger = structlog.get_logger(__name__)

# AaaS lang code -> tesseract language string. Government notices mix
# scripts freely, so the Indic hints always ride with eng.
_TESS_LANGS = {
    "or": "ori+eng",
    "hi": "hin+eng",
    "en": "eng",
    "auto": "ori+eng",
}

# Standard Windows install location (winget / UB-Mannheim installer) —
# probed when the configured command isn't on PATH, because a fresh
# install doesn't reach shells that were already open.
_WINDOWS_DEFAULT = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")

# A rendered PDF page whose text layer has at least this many
# characters is treated as born-digital; below it, we assume a scan
# (stamps/signatures often produce a few stray glyphs).
_TEXT_LAYER_MIN_CHARS = 30

_RENDER_SCALE = 2.5  # ~180 dpi — plenty for print-size notice text


class TesseractOcrEngine:
    name = "tesseract"

    def __init__(
        self,
        *,
        tesseract_cmd: str = "tesseract",
        tessdata_dir: str = "",
        max_pages: int = 10,
    ) -> None:
        self._cmd = tesseract_cmd
        self._tessdata_dir = tessdata_dir
        self._max_pages = max_pages
        self._loaded = False

    async def load(self) -> None:
        """Resolve the binary and probe it; raises if OCR can't work."""
        import os  # noqa: PLC0415

        import pytesseract  # noqa: PLC0415 — optional extra

        resolved = self._resolve_cmd()
        if resolved is None:
            raise RuntimeError(
                "tesseract binary not found — install it (winget install "
                "UB-Mannheim.TesseractOCR) or set AAAS_TRANSLATE_TESSERACT_CMD"
            )
        pytesseract.pytesseract.tesseract_cmd = resolved
        if self._tessdata_dir:
            # Env var rather than `--tessdata-dir "<path>"`: pytesseract
            # splits config with posix=False on Windows, which leaves
            # literal quotes in the argument and breaks paths with
            # spaces (like this repo's). The subprocess inherits this.
            os.environ["TESSDATA_PREFIX"] = self._tessdata_dir
        version = await asyncio.to_thread(pytesseract.get_tesseract_version)
        logger.info(
            "translate.ocr_engine_ready",
            engine=self.name,
            cmd=resolved,
            version=str(version),
            tessdata_dir=self._tessdata_dir or "(system default)",
        )
        self._loaded = True

    def _resolve_cmd(self) -> str | None:
        for candidate in (self._cmd, "tesseract"):
            if candidate and shutil.which(candidate):
                return candidate
        if _WINDOWS_DEFAULT.is_file():
            return str(_WINDOWS_DEFAULT)
        return None

    async def recognize(
        self, data: bytes, *, media_type: str, lang: str
    ) -> OcrResult:
        if not self._loaded:
            raise RuntimeError("OCR engine not loaded")
        key = lang.lower().split("-")[0]
        tess_lang = _TESS_LANGS.get(key, _TESS_LANGS["auto"])
        if media_type == "application/pdf":
            pages = await asyncio.to_thread(self._recognize_pdf, data, tess_lang)
        else:
            pages = await asyncio.to_thread(self._recognize_image, data, tess_lang)
        text = "\n\n".join(p.text for p in pages if p.text).strip()
        return OcrResult(
            text=text,
            pages=pages,
            lang=key if key in _TESS_LANGS else "auto",
            engine=self.name,
        )

    # ---- blocking workers (run in a thread) ----

    def _ocr_pil_image(self, image, tess_lang: str) -> str:
        import pytesseract  # noqa: PLC0415

        gray = image.convert("L")
        return pytesseract.image_to_string(gray, lang=tess_lang).strip()

    def _recognize_image(self, data: bytes, tess_lang: str) -> list[OcrPage]:
        from PIL import Image, UnidentifiedImageError  # noqa: PLC0415

        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except UnidentifiedImageError as exc:
            raise ValueError(f"Could not decode image: {exc}") from exc
        return [OcrPage(page=1, text=self._ocr_pil_image(image, tess_lang), source="ocr")]

    def _recognize_pdf(self, data: bytes, tess_lang: str) -> list[OcrPage]:
        import pypdfium2 as pdfium  # noqa: PLC0415

        try:
            doc = pdfium.PdfDocument(data)
        except Exception as exc:  # pdfium raises its own error types
            raise ValueError(f"Could not open PDF: {exc}") from exc
        pages: list[OcrPage] = []
        try:
            count = min(len(doc), self._max_pages)
            for i in range(count):
                page = doc[i]
                textpage = page.get_textpage()
                layer = (textpage.get_text_range() or "").strip()
                textpage.close()
                if len(layer) >= _TEXT_LAYER_MIN_CHARS:
                    pages.append(OcrPage(page=i + 1, text=layer, source="text-layer"))
                    continue
                bitmap = page.render(scale=_RENDER_SCALE)
                image = bitmap.to_pil()
                pages.append(
                    OcrPage(
                        page=i + 1,
                        text=self._ocr_pil_image(image, tess_lang),
                        source="ocr",
                    )
                )
        finally:
            doc.close()
        return pages
