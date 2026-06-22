from __future__ import annotations

from io import BytesIO
import logging

import requests

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover - optional runtime dependency guard
    Image = None
    ImageOps = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional runtime dependency guard
    pytesseract = None

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class ImageTextOcrReader:
    def __init__(
        self,
        *,
        language: str = "kor+eng",
        timeout_seconds: float = 10.0,
        user_agent: str = DEFAULT_USER_AGENT,
        tesseract_cmd: str | None = None,
    ) -> None:
        self._language = language
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self._warned_unavailable = False
        self._warned_tesseract_missing = False
        self._tesseract_missing = False

        if pytesseract is not None and tesseract_cmd is not None and tesseract_cmd.strip():
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd.strip()

    def read_text(self, image_url: str) -> str | None:
        if not self._is_available():
            return None
        if self._tesseract_missing:
            return None

        try:
            response = requests.get(
                image_url,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning(
                "이미지 OCR 다운로드 실패",
                extra={"image_url": image_url, "error": str(exc)},
            )
            return None

        content = response.content
        if not content:
            return None

        try:
            image = Image.open(BytesIO(content))
        except Exception as exc:
            logger.warning(
                "이미지 OCR 디코딩 실패",
                extra={"image_url": image_url, "error": str(exc)},
            )
            return None

        # OCR 인식률을 높이기 위해 기본 보정본 2개를 시도한다.
        candidates = [image, self._preprocess(image)]
        texts: list[str] = []
        for prepared in candidates:
            text = self._extract_text(prepared)
            if text:
                texts.append(text)

        if not texts:
            return None
        return max(texts, key=len)

    def _is_available(self) -> bool:
        if pytesseract is not None and Image is not None and ImageOps is not None:
            return True
        if not self._warned_unavailable:
            self._warned_unavailable = True
            logger.warning(
                "OCR 비활성화: pytesseract 또는 Pillow가 없습니다. "
                "requirements 설치 및 tesseract 실행 파일을 확인하세요."
            )
        return False

    def _extract_text(self, image) -> str | None:
        try:
            text = pytesseract.image_to_string(
                image,
                lang=self._language,
                config="--psm 6",
            )
        except Exception as exc:
            if self._is_tesseract_not_found(exc):
                self._tesseract_missing = True
                if not self._warned_tesseract_missing:
                    self._warned_tesseract_missing = True
                    logger.warning(
                        "OCR 비활성화: tesseract 실행 파일을 찾지 못했습니다. "
                        "CRAWLER_DTRAIL_TESSERACT_CMD 또는 PATH를 확인하세요."
                    )
                return None
            logger.warning("이미지 OCR 실행 실패", extra={"error": str(exc)})
            return None

        lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
        normalized = "\n".join(lines)
        if not normalized.strip():
            return None
        return normalized

    @staticmethod
    def _preprocess(image):
        grayscale = image.convert("L")
        autocontrast = ImageOps.autocontrast(grayscale)
        return autocontrast.point(lambda value: 255 if value > 160 else 0)

    @staticmethod
    def _is_tesseract_not_found(exc: Exception) -> bool:
        message = str(exc).lower()
        if "tesseract" not in message:
            return False
        return "not installed" in message or "not found" in message
