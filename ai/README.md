# ai (담당: 서준호)

옷 사진 분석 추론 서버. 백엔드(Spring)가 HTTP로 호출합니다.

- Python 버전: 3.11 (팀 통일)
- 실행 방법 (정해지면 수정):
  ```bash
  python -m venv .venv
  .venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000
  ```

## 백엔드와 약속할 API (초안 · 첫날 확정)

`POST /analyze` (multipart, 필드명 `file`)

```json
{
  "category": {"label": "OUTER", "confidence": 0.87,
               "candidates": [{"label": "OUTER", "score": 0.87}, {"label": "TOP", "score": 0.09}]},
  "colors": [{"name": "카멜", "hex": "#C19A6B", "ratio": 0.62}],
  "elapsedMs": 420,
  "modelVersion": "모델명@버전"
}
```

- `category.label` 은 백엔드와 같은 값만 사용: `TOP` `PANTS` `SKIRT` `OUTER` `SHOES`
- `confidence` 가 낮으면 화면에서 "확인해 주세요" 로 표시합니다.

## 평가 기록

`docs/` 에 모델 후보별 종류 정확도, 색상 일치율, 사진당 처리 시간을 남겨 주세요.
평가용 사진은 학습에 쓰지 않고 따로 보관합니다. 모델 가중치 파일은 용량이 커서 커밋하지 않습니다.

## 사용한 모델·데이터 출처

| 이름 | 라이선스 | 링크 | 용도 |
|---|---|---|---|
|  |  |  |  |
