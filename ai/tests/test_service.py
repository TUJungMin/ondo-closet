"""FastAPI 연결부 확인. 모델을 올리지 않는 경로만 다룬다."""

import threading
import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from ondo_ai.sample import autumn_wardrobe  # noqa: E402
from ondo_ai.service import app  # noqa: E402

client = TestClient(app)


def _request(pinned_id=2):
    return {
        "wardrobe": [g.model_dump(mode="json") for g in autumn_wardrobe()],
        "pinned_id": pinned_id,
        "weather": {"temp_c": 14, "sky": "흐림"},
        "place": "일상",
        "today": "2026-11-18",
    }


def test_health():
    assert client.get("/ai/health").json() == {"status": "ok"}


class _FakeAnalyzer:
    """모델 대신 쓰는 가짜. warmup이 release가 풀릴 때까지 끝나지 않게 해 '올리는 중'을 만든다."""

    device = "cpu"

    def __init__(self, error=None):
        self.calls = []
        self.started = threading.Event()
        self.release = threading.Event()
        self.error = error

    def warmup(self, outfit=False):
        self.calls.append(outfit)
        self.started.set()
        assert self.release.wait(5)
        if self.error:
            raise self.error


def _wait_until_ok(http, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if http.get("/ai/health").json() == {"status": "ok"}:
            return True
        time.sleep(0.01)
    return False


def test_startup_does_not_warm_up_by_default(monkeypatch):
    monkeypatch.delenv("ONDO_WARMUP", raising=False)
    fake = _FakeAnalyzer()
    monkeypatch.setattr("ondo_ai.vision.get_analyzer", lambda: fake)
    with TestClient(app) as started:
        assert started.get("/ai/health").json() == {"status": "ok"}
    assert fake.calls == []


def test_startup_warmup_reports_loading_then_ok(monkeypatch):
    monkeypatch.setenv("ONDO_WARMUP", "outfit")
    fake = _FakeAnalyzer()
    monkeypatch.setattr("ondo_ai.vision.get_analyzer", lambda: fake)
    with TestClient(app) as started:
        assert fake.started.wait(5)
        assert started.get("/ai/health").json() == {"status": "loading"}
        # 추천은 모델을 쓰지 않으므로 올리는 중에도 응답한다
        assert started.post("/ai/recommend", json=_request()).status_code == 200
        fake.release.set()
        assert _wait_until_ok(started)
    assert fake.calls == [True]  # 검출 모델까지: warmup(outfit=True)


def test_startup_warmup_failure_still_ends_ok(monkeypatch):
    monkeypatch.setenv("ONDO_WARMUP", "outfit")
    fake = _FakeAnalyzer(error=RuntimeError("가중치를 내려받지 못함"))
    monkeypatch.setattr("ondo_ai.vision.get_analyzer", lambda: fake)
    with TestClient(app) as started:
        assert fake.started.wait(5)
        assert started.get("/ai/health").json() == {"status": "loading"}
        fake.release.set()
        assert _wait_until_ok(started)


def test_unknown_warmup_value_is_ignored(monkeypatch):
    monkeypatch.setenv("ONDO_WARMUP", "yes")
    fake = _FakeAnalyzer()
    monkeypatch.setattr("ondo_ai.vision.get_analyzer", lambda: fake)
    with TestClient(app) as started:
        assert started.get("/ai/health").json() == {"status": "ok"}
    assert fake.calls == []


def test_recommend_over_http():
    response = client.post("/ai/recommend", json=_request())
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 3
    first = body["recommendations"][0]
    assert first["items"][0] == {
        "slot": "상의",
        "garment_id": 2,
        "name": "베이지 니트",
        "category": "상의",
        "pinned": True,
    }
    assert first["reason"] and {b["kind"] for b in first["basis"]} >= {"날씨", "고정 옷", "체감 기록"}
    assert {e["status"] for e in body["excluded"]} == {"세탁", "건조", "수선"}


def test_unknown_pinned_garment_is_404():
    assert client.post("/ai/recommend", json=_request(pinned_id=999)).status_code == 404


def test_invalid_enum_value_is_422():
    request = _request()
    request["place"] = "우주"
    assert client.post("/ai/recommend", json=request).status_code == 422


def test_non_image_upload_is_400():
    for path in ("/ai/analyze", "/ai/analyze-outfit"):
        response = client.post(path, files={"file": ("memo.txt", b"not an image", "text/plain")})
        assert response.status_code == 400, path


def test_api_lists_both_analysis_routes():
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/ai/analyze", "/ai/analyze-outfit", "/ai/recommend", "/ai/warmup", "/ai/health"} <= set(paths)
