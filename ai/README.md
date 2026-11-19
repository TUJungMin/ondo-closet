# ai (담당: 서준호)

옷 사진 분석과 코디 추천을 맡는 파이썬 모듈이자 추론 서버. 백엔드(Spring)가 HTTP로 호출한다.
모델은 모두 이 서버 안에서 실행하고, 사진을 외부 API로 보내지 않는다.

| 기능 | 상태 |
|---|---|
| 옷 한 벌 사진 분석 (배경 제거 · 대표색 · 종류/보온성/스타일 제안) | 구현 |
| 옷이 여러 벌 찍힌 사진을 옷별로 나눠 분석 | 구현 (착용 사진 1장으로만 확인) |
| 한 벌 고정 코디 추천 (날씨 · 장소 · 옷 상태 · 체감 기록 · 거절 이유) | 구현 |
| 백엔드와 약속한 `/analyze` 응답 형식 맞추기 | **아직 안 맞음** (맨 아래 참고) |

테스트 111개 통과. 팀이 찍은 사진으로 한 정식 정확도 평가는 아직 없다 ([docs/eval.md](docs/eval.md)).

> 이 문서의 경로와 명령은 모두 `ai/` 폴더 기준이다.

## 실행

- Python 3.11 (팀 통일). 개발과 테스트는 3.12에서 했고 3.10 이상이면 동작하도록 썼다. 3.11에서는 아직 돌려 보지 않았다.
- 모델을 처음 쓸 때 가중치 약 1.3GB를 Hugging Face에서 내려받는다. NVIDIA GPU가 있으면 사진당 약 0.3초, CPU만 있으면 2.5~10초.

```bash
python -m venv .venv
```

PyTorch는 장치에 맞는 빌드를 먼저 설치한다. NVIDIA GPU(CUDA 12.8)인 경우:

```bash
.venv/Scripts/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

GPU가 없으면 주소 끝의 `cu128`을 `cpu`로 바꾼다. 이어서:

```bash
.venv/Scripts/python -m pip install -r requirements.txt
```

```bash
.venv/Scripts/python -m uvicorn main:app --port 8000
```

띄운 뒤 http://127.0.0.1:8000/docs 에서 요청·응답 형식을 보고 바로 호출해 볼 수 있다.
macOS·Linux에서는 `.venv/Scripts/python` 대신 `.venv/bin/python`을 쓴다.

설치 확인 (모델을 내려받지 않는다):

```bash
.venv/Scripts/python -m pytest -q
```

## 구조

```
ai/
├─ main.py                  추론 서버 진입점 (uvicorn main:app)
├─ requirements.txt         설치 목록 (pyproject.toml의 의존성을 그대로 설치)
├─ requirements.lock.txt    테스트를 통과한 버전 고정 목록
├─ pyproject.toml
├─ CLAUDE.md                AI 코딩 도구용 작업 지침 (범위, 데이터 기준)
├─ docs/
│  ├─ eval.md               처리 시간 측정값, 확인된 한계, 평가 방법
│  └─ external-resources.md 모델·라이브러리·데이터 출처와 라이선스 (제출 별첨용)
├─ ondo_ai/
│  ├─ schemas.py            주고받는 데이터 형식
│  ├─ palette.py            색 이름표 19색, 색 조합 규칙
│  ├─ config.py             모델 리비전, 기준값, 환경 변수
│  ├─ vision/               이미지 분석
│  │  ├─ pipeline.py          전체 흐름을 묶은 GarmentAnalyzer
│  │  ├─ detect.py            여러 옷 사진에서 옷 위치 찾기 (yolos-fashionpedia)
│  │  ├─ background.py        배경 제거 (BiRefNet)
│  │  ├─ color.py             대표색 계산 (k-means → 색 이름)
│  │  ├─ classifier.py        제로샷 분류기 (FashionSigLIP)
│  │  ├─ attributes.py        분류 확률 → 종류·보온성·스타일 제안
│  │  └─ labels.py            분류 후보 문구
│  ├─ recommend/            추천 엔진 (torch 불필요)
│  │  ├─ engine.py            조합 · 점수 · 이유 문장 · 근거
│  │  ├─ thermal.py           기온별 보온 기준, 체감 기록 → 개인 보정
│  │  └─ feedback.py          거절 이유 → 순위 조정
│  ├─ service.py            FastAPI 라우터와 앱
│  ├─ cli.py                명령줄 도구
│  └─ sample.py             예시 옷장 30벌 (글자 정보만)
├─ scripts/                 evaluate.py(정확도 평가), benchmark.py(처리 시간)
└─ tests/                   pytest
```

## 동작 흐름

```
옷 사진 ──▶ 배경 제거 ──▶ 대표색 계산 ──▶ 종류·보온성·스타일 제안 ──▶ 사용자가 확인·수정 후 저장
                                                                          │
고정한 옷 한 벌 + 날씨 + 장소 + 옷 상태 + 착용·거절 기록 ◀───────────────┘
        │
        ▼
   추천 엔진 ──▶ 코디 여러 개 (한 줄 이유 + 근거) ──▶ 착용 후 체감 기록 · 거절 이유 ──▶ 다음 추천에 반영
```

- 사진은 옷 한 벌만 찍힌 단품 사진이 기준이다. 옷이 여러 벌 찍힌 사진(착용 사진 등)은 옷 위치를 먼저 찾아 옷별로 나눈 뒤 같은 과정을 거친다.
- 모델은 모두 서버 안에서 실행한다. 사진을 외부 API로 보내지 않는다.
- 분석 결과는 "AI 제안"이다. 확신이 낮으면 값을 비워 두고 사용자가 직접 고르게 한다.
- 추천은 규칙과 점수로 계산한다. 생성형 AI를 쓰지 않는다.

## 사용법

### 1. 코디 추천

예시 옷장 30벌로 바로 확인할 수 있다. `--pin`은 고정할 옷 번호다(2 = 베이지 니트).

```bash
.venv/Scripts/python -m ondo_ai demo --pin 2 --temp 12 --sky 흐림
```

추천 3개가 나온다. 아래는 그중 첫 번째까지의 출력이다.

```
체감 12.0°C, 개인 보정 +0.0°C → 기준 12.0°C
  - 제외: 회색 맨투맨 (건조)
  - 제외: 남색 줄무늬 티셔츠 (세탁)
  - 제외: 베이지 롱 스커트 (수선)

1. [고정] 베이지 니트 + 진청 청바지 + 회색 카디건 + 흰색 스니커즈  (93.3점)
   체감 12°C라 회색 카디건을 걸쳤고, 고정한 베이지 니트에 진청 청바지를 맞춰 깔끔하게 어울려요.
   · 날씨: 기온 12°C, 체감 12°C, 흐림
   · 고정 옷: 베이지 니트 고정 (보온 4단계, 캐주얼, 베이지)
   · 체감 기록: 아직 체감 기록이 없어 기본 기준으로 맞췄어요
   · 장소: '일상'에 어울리는 스타일을 우선했어요
   · 옷 상태: 세탁·건조·수선 중인 옷 3벌은 빼고 골랐어요
```

바꿔 볼 수 있는 값:

| 옵션 | 뜻 | 값 |
|---|---|---|
| `--pin` | 고정할 옷 번호 | 1~30 (`ondo_ai/sample.py`) |
| `--temp` | 기온 °C | 숫자 |
| `--temp-min`, `--temp-max` | 최저·최고 기온 (일교차 반영) | 숫자 |
| `--wind` | 풍속 m/s (체감 온도 추정) | 숫자 |
| `--sky` | 하늘 상태 | 맑음 · 흐림 · 비 · 눈 |
| `--place` | 장소 | 일상 · 출근 · 격식 · 데이트 · 야외활동 · 운동 |
| `--top-k` | 추천 개수 | 기본 3 |
| `--json` | 응답을 JSON 그대로 출력 | — |

파이썬 코드에서 부를 때:

```python
from ondo_ai import RecommendRequest, Weather, recommend
from ondo_ai.sample import autumn_wardrobe

result = recommend(
    RecommendRequest(
        wardrobe=autumn_wardrobe(),          # 실제로는 DB에서 읽은 옷 목록
        pinned_id=2,                         # 고정한 옷
        weather=Weather(temp_c=12, sky="흐림"),
        place="일상",
        wear_history=[],                     # 착용 후 체감 기록 (추웠어요·적당했어요·더웠어요)
        rejections=[],                       # 거절 기록 (이유 포함)
    )
)
for rec in result.recommendations:
    print(rec.rank, [item.name for item in rec.items], rec.reason)
```

엔진은 상태를 저장하지 않는다. 착용 기록과 거절 기록을 요청에 함께 넣으면 그만큼 반영된다.

### 2. 옷 사진 분석

옷 한 벌이 찍힌 사진을 분석한다. 처음 실행할 때 모델을 내려받는다(약 1.2GB).

```bash
.venv/Scripts/python -m ondo_ai analyze 사진.jpg --cutout 결과.png
```

`--cutout`에 준 경로로 배경을 지운 PNG가 저장되고, 분석 결과가 JSON으로 출력된다. 아래는 베이지 트렌치코트 사진의 실제 출력에서 후보 목록 일부를 줄인 것이다.

```json
{
  "source": "ai",
  "category": {
    "value": "겉옷",
    "confidence": 0.9996,
    "candidates": [{"label": "겉옷", "score": 0.9996}, {"label": "상의", "score": 0.0003}]
  },
  "subtype": {"value": "트렌치코트", "confidence": 0.6037},
  "name_suggestion": "베이지 트렌치코트",
  "colors": [{"name": "베이지", "hex": "#ad9b7a", "ratio": 0.951}],
  "warmth": {"value": 3, "confidence": 0.6037},
  "style": {"value": "포멀", "confidence": 0.483},
  "waterproof": false,
  "grip": false,
  "cutout_path": "결과.png",
  "foreground_ratio": 0.4418,
  "warnings": []
}
```

- `value`가 `null`이면 AI가 확신하지 못한 것이다. `candidates`를 선택지로 보여주고 사용자가 고르게 한다.
- `warnings`에는 사용자에게 그대로 보여줄 수 있는 안내 문장이 담긴다(예: 옷을 가려내지 못함).
- 이 명령은 옷 한 벌만 찍힌 사진용이다. 여러 벌이 찍힌 사진은 아래 3번을 쓴다.
- 사진 여러 장을 한 번에 넣고 `--cutout` 대신 `--cutout-dir 결과폴더`를 주면, 배경 제거 이미지가 종류별 폴더(`상의` · `하의` · `겉옷` · `신발`, 종류를 정하지 못하면 `미분류`)에 `사진이름.png`로 나뉘어 저장된다.

파이썬 코드에서 부를 때:

```python
from ondo_ai.vision import get_analyzer

analyzer = get_analyzer()
analyzer.warmup()        # 서버 시작 때 한 번. 모델을 올리고 첫 요청 지연을 없앤다
result = analyzer.analyze("사진.jpg", cutout_path="cutouts/1.png")
print(result.category.value, [c.name for c in result.colors], result.warnings)
```

### 3. 옷이 여러 벌 찍힌 사진 분석

착용 사진처럼 한 장에 옷이 여러 벌 있으면, 옷 위치를 먼저 찾아 옷별로 나눠 분석한다. 처음 실행할 때 검출 모델(약 0.1GB)을 추가로 내려받는다.

```bash
.venv/Scripts/python -m ondo_ai analyze-outfit 착용사진.jpg --cutout-dir 결과폴더
```

옷마다 배경을 지운 PNG가 종류별 폴더에 나뉘어 저장된다. 파일 이름은 `사진이름_번호.png`이고 번호는 사진의 위에서 아래 순서다.

```
결과폴더/
├─ 상의/   착용사진_1.png
├─ 하의/   착용사진_2.png     (바지와 스커트가 함께 들어간다)
├─ 겉옷/
└─ 신발/   착용사진_3.png
```

같은 폴더에 여러 사진을 차례로 돌리면 종류별로 쌓인다. 아래는 후드티·와이드 팬츠·스니커즈를 입고 가방을 멘 사진의 실제 출력을 줄인 것이다.

```json
{
  "source": "ai",
  "items": [
    {
      "box": [0.3292, 0.0049, 0.9022, 0.4814],
      "detector_label": "jacket",
      "detector_score": 0.7345,
      "analysis": {
        "category": {"value": "상의", "confidence": 0.9648},
        "subtype": {"value": "후드티"},
        "name_suggestion": "갈색 후드티",
        "colors": [{"name": "갈색", "hex": "#423529", "ratio": 0.934}],
        "warmth": {"value": 4},
        "style": {"value": "스트릿"}
      }
    },
    {
      "box": [0.3409, 0.43, 0.7727, 0.9713],
      "detector_label": "pants",
      "detector_score": 0.9746,
      "analysis": {"name_suggestion": "검정 코듀로이 팬츠", "colors": [{"name": "검정", "hex": "#2b2b23", "ratio": 0.964}]}
    },
    {
      "box": [0.3396, 0.9115, 0.7154, 0.9794],
      "detector_label": "shoe",
      "detector_score": 0.9729,
      "analysis": {"name_suggestion": "아이보리 스니커즈", "colors": [{"name": "아이보리", "hex": "#e4dfcf", "ratio": 0.466}]}
    }
  ],
  "skipped": ["가방"],
  "warnings": []
}
```

- `items`는 사진의 위에서 아래 순서다. 옷마다 `analysis`는 한 벌 분석과 같은 형식이다.
- `box`는 사진 안에서의 위치다(왼쪽, 위, 오른쪽, 아래. 가로·세로 대비 0~1). 화면에서 사진 위에 상자를 그려 사용자가 확인하게 할 수 있다.
- `skipped`에는 찾았지만 옷장 종류가 아니라 뺀 것의 이름이 담긴다(가방 · 모자 · 목도리 · 원피스 · 점프수트).
- 신발은 좌우 두 짝을 한 벌로 묶는다.

알아 둘 한계:

- 사람이 입은 사진에 맞는 방식이다. 옷 한 벌만 찍은 단품 사진, 특히 신발은 찾지 못할 수 있으니 2번의 한 벌 분석을 쓴다.
- 겹쳐 입어 대부분 가려진 옷은 찾지 못한다. 같은 색 옷을 겹쳐 입으면 안쪽 옷을 놓친다.
- 배경을 지운 이미지에 손·휴대폰·가방끈이 함께 남을 수 있다.
- 원본 사진은 저장하지 않지만, 얼굴이 나왔는지는 확인하지 않는다. 얼굴이 나오지 않게 찍도록 화면에서 안내해야 한다.

파이썬 코드에서 부를 때:

```python
from ondo_ai.vision import get_analyzer

analyzer = get_analyzer()
analyzer.warmup(outfit=True)     # 검출 모델까지 미리 올린다
result = analyzer.analyze_outfit("착용사진.jpg", cutout_dir="cutouts/outfit")
for item in result.items:
    print(item.box, item.analysis.name_suggestion)
print(result.skipped, result.warnings)
```

### 4. 서버로 띄우기

```bash
.venv/Scripts/python -m uvicorn ondo_ai.service:app --port 8000
```

띄운 뒤 http://127.0.0.1:8000/docs 에서 요청·응답 형식을 보고 바로 호출해 볼 수 있다.

| 주소 | 입력 | 출력 |
|---|---|---|
| `GET /ai/health` | — | `{"status": "ok"}` |
| `POST /ai/warmup` | (선택) `?outfit=true` | 모델을 미리 메모리에 올린다. `outfit=true`면 검출 모델까지 |
| `POST /ai/analyze` | multipart `file` (옷 한 벌 사진, 15MB 이하) | 분석 결과 + `cutout_png_base64` |
| `POST /ai/analyze-outfit` | multipart `file` (옷이 여러 벌 찍힌 사진) | 옷별 분석 결과 목록. 옷마다 `box`와 `cutout_png_base64` |
| `POST /ai/recommend` | 아래 형식의 JSON | 추천 목록 + 제외된 옷 + 근거 |

`POST /ai/recommend` 요청 예시:

```json
{
  "wardrobe": [
    {"id": 1, "name": "베이지 니트", "category": "상의", "colors": ["베이지"], "warmth": 4, "style": "캐주얼"},
    {"id": 2, "name": "진청 청바지", "category": "바지", "colors": ["남색"], "warmth": 3, "style": "캐주얼"},
    {"id": 3, "name": "베이지 트렌치코트", "category": "겉옷", "colors": ["베이지"], "warmth": 3, "style": "포멀"},
    {"id": 4, "name": "흰색 스니커즈", "category": "신발", "colors": ["흰색"], "warmth": 3, "style": "캐주얼", "grip": true},
    {"id": 5, "name": "회색 맨투맨", "category": "상의", "colors": ["회색"], "warmth": 3, "status": "세탁"}
  ],
  "pinned_id": 1,
  "weather": {"temp_c": 12, "sky": "흐림"},
  "place": "일상"
}
```

응답(첫 번째 추천만, 일부 줄임):

```json
{
  "recommendations": [
    {
      "rank": 1,
      "items": [
        {"slot": "상의", "garment_id": 1, "name": "베이지 니트", "category": "상의", "pinned": true},
        {"slot": "하의", "garment_id": 2, "name": "진청 청바지", "category": "바지", "pinned": false},
        {"slot": "겉옷", "garment_id": 3, "name": "베이지 트렌치코트", "category": "겉옷", "pinned": false},
        {"slot": "신발", "garment_id": 4, "name": "흰색 스니커즈", "category": "신발", "pinned": false}
      ],
      "score": 85.0,
      "reason": "체감 12°C라 베이지 트렌치코트를 걸쳤고, 고정한 베이지 니트에 진청 청바지를 맞춰 깔끔하게 어울려요.",
      "basis": [
        {"kind": "날씨", "text": "기온 12°C, 체감 12°C, 흐림"},
        {"kind": "고정 옷", "text": "베이지 니트 고정 (보온 4단계, 캐주얼, 베이지)"},
        {"kind": "체감 기록", "text": "아직 체감 기록이 없어 기본 기준으로 맞췄어요"},
        {"kind": "장소", "text": "'일상'에 어울리는 스타일을 우선했어요"},
        {"kind": "옷 상태", "text": "세탁·건조·수선 중인 옷 1벌은 빼고 골랐어요"}
      ],
      "breakdown": {"보온": 0.841, "색": 0.943, "스타일·장소": 0.84, "날씨 대비": 1.0, "선호": 0.5}
    }
  ],
  "excluded": [
    {"garment_id": 5, "name": "회색 맨투맨", "status": "세탁", "text": "세탁 중이라 추천에서 뺐어요"}
  ],
  "warnings": []
}
```

기존 FastAPI 백엔드 안에 붙일 때는 서버를 따로 띄우지 않고 라우터만 넣는다.

```python
from ondo_ai.service import router

app.include_router(router)
```

### 값 목록

요청과 응답에 쓰는 값은 화면에 보이는 한글 그대로다. 정의는 `ondo_ai/schemas.py`에 있다.

| 항목 | 값 |
|---|---|
| 종류 `category` | 상의 · 바지 · 스커트 · 겉옷 · 신발 |
| 상태 `status` | 입을 수 있음 · 세탁 · 건조 · 수선 |
| 보온성 `warmth` | 1(한여름용) ~ 5(한겨울용) |
| 스타일 `style` | 캐주얼 · 포멀 · 스포티 · 스트릿 · 페미닌 |
| 장소 `place` | 일상 · 출근 · 격식 · 데이트 · 야외활동 · 운동 |
| 하늘 `sky` | 맑음 · 흐림 · 비 · 눈 |
| 체감 `feeling` | 추웠어요 · 적당했어요 · 더웠어요 |
| 거절 이유 `reason` | 너무 얇음 · 색이 안 맞음 · 장소에 안 맞음 · 직접 입력 |
| 색 `colors` | 검정 · 흰색 · 회색 · 아이보리 · 베이지 · 카멜 · 갈색 · 카키 · 남색 · 파랑 · 하늘색 · 초록 · 민트 · 노랑 · 주황 · 빨강 · 버건디 · 분홍 · 보라 |

스타일·장소 목록과 보온성 단계는 지침에 없어 넣은 기본안이다. 팀에서 확정하면 `schemas.py`만 고치면 된다.

### 환경 변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `ONDO_DEVICE` | `auto` | 모델 실행 장치. `auto`는 GPU가 있으면 GPU. `cuda` · `cpu`로 고정 가능 |
| `ONDO_SEGMENT_SIZE` | `1024` | 배경 제거 입력 크기. CPU 서버에서는 `512`로 줄이면 약 4배 빨라진다 |
| `ONDO_MAX_IMAGE_SIDE` | `1600` | 분석 전에 원본 사진을 이 크기 이하로 줄인다 |
| `ONDO_CUTOUT_MAX_SIDE` | `800` | 저장하는 배경 제거 이미지의 최대 크기 |
| `ONDO_CLASSIFY_ON` | `cutout` | 분류에 넣는 이미지. `cutout`(배경 지운 것) · `original` |

## 평가와 측정

평가용 사진 폴더와 정답표(`labels.csv`)를 준비해 정확도를 잰다. 정답표 형식은 [docs/eval.md](docs/eval.md) 4장에 있다.

```bash
.venv/Scripts/python scripts/evaluate.py 평가폴더 --labels 평가폴더/labels.csv
```

배포할 서버에서 사진당 처리 시간을 잰다.

```bash
.venv/Scripts/python scripts/benchmark.py 평가폴더 --device cpu
```

팀이 직접 찍은 사진으로 한 정식 정확도 평가는 아직 하지 않았다. 지금 `docs/eval.md`에 있는 숫자는 처리 시간과 6장 동작 확인이다.

## 화면에서 알아 둘 것

- **AI 제안 표시**: `AnalysisResult.source`는 항상 `"ai"`다. 종류·세부 종류·보온성·스타일은 각각 `value`(제안값), `confidence`, `candidates`(상위 후보 3개)를 가진다.
- **값이 비어 올 수 있다**: 확신이 낮거나 옷을 가려내지 못하면 `value`가 `null`, `colors`가 빈 배열로 오고 `warnings`에 사용자에게 보여줄 문장이 담긴다. 이때는 `candidates`를 선택지로 보여주고 직접 고르게 한다.
- **여러 옷 사진**: `/ai/analyze-outfit`은 찾은 옷마다 사진 안 위치(`box`)와 분석 결과를 돌려준다. 사진 위에 상자를 그려 보여 주고, 사용자가 옷별로 확인·수정한 뒤 저장할 것만 고르게 한다. 겹쳐 입어 가려진 옷과 단품 신발 사진은 놓칠 수 있으니 "직접 추가" 길을 남겨 둔다. 원본 사진은 AI 모듈이 저장하지 않으며, 얼굴이 나왔는지는 확인하지 않는다. 한계는 `docs/eval.md` 2-1장에 있다.
- **추천 카드**: `Recommendation.reason`이 "왜 이 조합인지" 한 줄, `basis`가 근거 목록(날씨 · 고정 옷 · 체감 기록 · 거절 이유 · 장소 · 옷 상태), `items[].pinned`가 고정한 옷이다.
- **제외된 옷**: `RecommendResult.excluded`에 세탁·건조·수선 중이라 뺀 옷이 이유와 함께 온다.
- **기록 저장은 백엔드 몫**: 엔진은 상태를 갖지 않는다. 착용 기록(`WearRecord`)과 거절 기록(`Rejection`)을 저장해 두었다가 추천 요청에 함께 넣어 주면 반영된다. 거절 기록에는 거절한 조합의 `item_ids`, `pinned_id`, 그때의 `temp_c`와 `place`를 같이 저장한다.

## 팀에서 확정이 필요한 값

명세(CLAUDE.md)에 없어 기본안을 넣어 둔 것들이다. 바꾸려면 `schemas.py`만 고치면 된다.

| 항목 | 현재 기본안 |
|---|---|
| 장소 목록 | 일상 · 출근 · 격식 · 데이트 · 야외활동 · 운동 |
| 스타일 목록 | 캐주얼 · 포멀 · 스포티 · 스트릿 · 페미닌 |
| 보온성 단계 | 1(한여름용) ~ 5(한겨울용) |
| 색 이름 | `palette.py`의 19색 |

## 조정하는 곳

| 바꾸고 싶은 것 | 파일 |
|---|---|
| 분류가 자주 틀리는 종류의 후보 문구 | `vision/labels.py` |
| "확신 낮음"으로 보고 비워 두는 기준 | `config.py` |
| 여러 옷 사진에서 옷으로 인정하는 점수·크기 기준 | `config.py`의 `DETECT_` 값 |
| 색 이름이 자주 틀리는 색 | `palette.py`에 견본 추가 |
| 기온별 옷 두께 기준 | `recommend/thermal.py`의 표 |
| 점수 가중치, 장소별 스타일 적합도 | `recommend/engine.py` 위쪽 |

## 조정하는 곳

| 바꾸고 싶은 것 | 파일 |
|---|---|
| 분류가 자주 틀리는 종류의 후보 문구 | `ondo_ai/vision/labels.py` |
| "확신 낮음"으로 보고 비워 두는 기준 | `ondo_ai/config.py` |
| 여러 옷 사진에서 옷으로 인정하는 점수·크기 기준 | `ondo_ai/config.py`의 `DETECT_` 값 |
| 색 이름이 자주 틀리는 색 | `ondo_ai/palette.py`에 견본 추가 |
| 기온별 옷 두께 기준 | `ondo_ai/recommend/thermal.py`의 표 |
| 점수 가중치, 장소별 스타일 적합도 | `ondo_ai/recommend/engine.py` 위쪽 |

## 백엔드와 맞춰야 할 것 (미해결)

아래 "초안"은 저장소를 처음 만들 때 적어 둔 약속이다. 지금 구현은 이와 다르다. 어느 쪽에 맞출지 정해야 한다.

| 항목 | 초안 (아래) | 지금 구현 |
|---|---|---|
| 주소 | `POST /analyze` | `POST /ai/analyze`, `POST /ai/analyze-outfit`, `POST /ai/recommend` |
| 종류 값 | `TOP` `PANTS` `SKIRT` `OUTER` `SHOES` | `상의` `바지` `스커트` `겉옷` `신발` |
| 종류 필드 | `category.label` | `category.value` (확신이 낮으면 `null`) |
| 스타일 값 (`docs/API.md`) | `MINIMAL` `CASUAL` `FORMAL` `SPORTY` | `캐주얼` `포멀` `스포티` `스트릿` `페미닌` |
| 색 | `color` 하나 (`docs/API.md`) | `colors` 최대 2개 |
| 처리 시간 · 모델 | `elapsedMs`, `modelVersion` | `timings_ms`(단계별), `models`(단계별) |
| 소재 `material` (`docs/API.md`) | 있음 | 분석하지 않음 |

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

## 사용한 모델·데이터 출처

전체 목록(라이브러리, 리비전, 동작 확인에 쓴 사진의 취급)은 [docs/external-resources.md](docs/external-resources.md)에 있다.

| 이름 | 라이선스 | 링크 | 용도 |
|---|---|---|---|
| Marqo/marqo-fashionSigLIP | Apache-2.0 | https://huggingface.co/Marqo/marqo-fashionSigLIP | 종류·세부 종류·보온성·스타일 제로샷 분류 |
| ZhengPeng7/BiRefNet | MIT | https://huggingface.co/ZhengPeng7/BiRefNet | 배경 제거 |
| valentinafevu/yolos-fashionpedia | MIT | https://huggingface.co/valentinafevu/yolos-fashionpedia | 여러 옷 사진에서 옷 위치 찾기 |
| patrickjohncyh/fashion-clip | MIT | https://huggingface.co/patrickjohncyh/fashion-clip | 평가 때 비교 기준선 (서비스에서는 쓰지 않음) |

저장소에 들어간 외부 데이터는 없다. 모델 가중치도 커밋하지 않는다.
