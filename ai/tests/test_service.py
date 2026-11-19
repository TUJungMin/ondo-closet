"""FastAPI 연결부 확인. 모델을 올리지 않는 경로만 다룬다."""

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
