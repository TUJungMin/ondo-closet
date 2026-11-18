"""추론 서버 진입점: `uvicorn main:app --port 8000`. 주소와 처리 내용은 ondo_ai/service.py에 있다."""

from ondo_ai.service import app

__all__ = ["app"]
