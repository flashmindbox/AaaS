"""TTS engine implementations.

The public surface is the ``TTSEngine`` Protocol plus a concrete
Meta MMS-TTS backend and its multi-language router. Swapping in a
different backend (ONNX-quantised variant, different VITS family)
becomes a one-file change and leaves the FastAPI layer untouched.
"""

from app.engine.base import TTSEngine, TTSResult
from app.engine.mms import EmptyTokenisationError, MMSEngine
from app.engine.multi import MultiLangMMSEngine, UnsupportedLanguageError

__all__ = [
    "EmptyTokenisationError",
    "MMSEngine",
    "MultiLangMMSEngine",
    "TTSEngine",
    "TTSResult",
    "UnsupportedLanguageError",
]
