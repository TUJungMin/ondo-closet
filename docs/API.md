# API 문서

> 백엔드 담당: 곽정민 · 로컬 주소 `http://localhost:8080` · 배포 주소는 루트 README 참고
> API를 바꾸면 이 문서도 같은 PR에서 고쳐 주세요.
> 2026-11-19 프론트·백엔드 형식 맞추기(AL-01~13) 반영. 값은 소문자, 필드 이름은 프론트 기준.

모든 응답은 JSON. 로그인이 필요한 API는 헤더에 `Authorization: Bearer <accessToken>`.

## 값 목록

| 항목 | 값 | 화면 글자 |
|---|---|---|
| `type` (종류) | `top` `pants` `skirt` `outer` `shoes` | 상의 · 바지 · 스커트 · 겉옷 · 신발 |
| `style` | `casual` `formal` `sporty` `street` `feminine` | 캐주얼 · 포멀 · 스포티 · 스트릿 · 페미닌 |
| `warm` (보온성) | `light` `medium` `warm` | 얇음 · 보통 · 따뜻함 |
| `place` | `daily` `office` `formal` `date` `outdoor` `sport` | 일상 · 출근·미팅 · 격식 · 카페·데이트 · 산책·야외 · 운동 |
| `sky` | `clear` `cloudy` `rain` `snow` | 맑음 · 흐림 · 비 · 눈 |

- 받을 때는 대문자도 허용하지만, 보낼 때는 항상 소문자다.
- `color` 는 `#rrggbb` (색 선택기 값 그대로). AI 추천에 보낼 때 서버가 가장 가까운 19색 이름으로 바꾼다.
- `warmScore` 는 1~5 세부값(1 한여름 ~ 5 한겨울). 몰라도 된다. light=2, medium=3, warm=4 로 저장되고,
  AI 분석 결과(draft)의 `warmScore` 를 그대로 보내면 패딩(5)·민소매(1) 같은 끝값이 지켜진다.

## 인증

| 메서드 | 경로 | 로그인 | 설명 |
|---|---|---|---|
| POST | `/api/auth/signup` | X | `{loginId, password, nickname}` → 토큰. loginId 영문·숫자·_ 4~20자, password 8~64자, nickname 20자 이하 |
| POST | `/api/auth/login` | X | `{loginId, password}` → 토큰 |
| POST | `/api/auth/guest` | X | 새 게스트 계정 + 샘플 옷장 12벌 → 토큰 |
| GET | `/api/me` | O | 내 정보 |

```json
{"accessToken":"eyJ...","tokenType":"Bearer","expiresIn":604800,
 "user":{"id":1,"loginId":"guest_3fa9c1d2e0","nickname":"게스트","guest":true,"warmthOffset":0}}
```

## 옷장

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/clothes` | 내 옷 전체, 최신순 (`?type=outer` 로 필터) |
| GET | `/api/clothes/{id}` | 한 벌 |
| POST | `/api/clothes` | 등록 (201) |
| PUT | `/api/clothes/{id}` | 전체 수정 (모든 필수 필드) |
| PATCH | `/api/clothes/{id}` | 부분 수정. 보낸 필드만 바뀜 |
| DELETE | `/api/clothes/{id}` | 삭제 (204) |
| POST | `/api/clothes/image` | 사진 파일만 따로 올리기 (form-data `file`, JPG/PNG/WEBP, 15MB 이하) → `{"photo":"http://localhost:8080/uploads/..."}` |

요청 (POST·PUT):
```json
{"name":"카멜 울 코트","type":"outer","color":"#c19a6b","material":"울","warm":"warm","warmScore":null,
 "style":"formal","water":false,"grip":false,"photo":"data:image/jpeg;base64,/9j/4AAQ...","aiTagged":false}
```
- 필수: `name`(60자 이하), `type`, `color`, `warm`, `style`. 나머지는 생략 가능.
- `photo` 에 넣을 수 있는 것:
  - 사진 데이터 `data:image/jpeg|png|webp;base64,...` (3MB 이하) → 서버가 파일로 저장
  - 서버에서 받은 사진 주소 (`http://localhost:8080/uploads/...`) → 그대로 유지
  - 빈 문자열 `""` → 사진 지우기 (PATCH)
- PATCH 예: `{"water": true}`, `{"photo": "data:image/jpeg;base64,..."}`, `{"warm": "light"}`

응답:
```json
{"id":7,"name":"카멜 울 코트","type":"outer","color":"#c19a6b","material":"울","warm":"warm","warmScore":4,
 "style":"formal","water":false,"grip":false,"photo":"http://localhost:8080/uploads/2b1e....jpg",
 "aiTagged":false,"lastWorn":null,"createdAt":"2026-11-19T11:20:31Z"}
```
- `photo` 는 전체 주소라 `img.src` 에 바로 넣으면 된다. 사진이 없으면 `null`.

## AI 옷 분석

| 메서드 | 경로 | 로그인 | 설명 |
|---|---|---|---|
| POST | `/api/clothes/analyze?mode=outfit` | O | 착용 사진(form-data `file`) → 상의·하의·겉옷·신발로 나눠 분석 |
| POST | `/api/clothes/analyze?mode=single` | O | 옷 한 벌 사진 (기본값) |
| GET | `/api/ai/health` | X | `{"ai":"ok"}` 또는 `{"ai":"unavailable"}` |

- 사진은 **줄이지 않은 원본 파일**(JPG/PNG/WEBP, 15MB 이하)을 보낸다. 첫 분석은 모델을 올리느라 수십 초~몇 분 걸릴 수 있다.
- 원본은 저장하지 않고, AI가 배경을 지운 옷 사진만 저장해 `draft.photo` 에 넣는다.
- `items[].draft` 는 `POST /api/clothes` 요청과 같은 모양이다. 확인·수정 후 그대로 보내면 저장된다.
- AI가 확신하지 못한 값은 `draft` 에서 `null`. `ai.needsReview=true` 면 빈 칸을 채우게 안내한다.
- AI 서버가 꺼져 있으면 503 `AI_UNAVAILABLE` → 직접 입력으로 넘어간다.

```json
{"mode":"outfit","elapsedMs":3120,"skipped":["가방"],"warnings":[],
 "items":[{"index":1,"box":[0.33,0.0,0.9,0.48],
   "draft":{"name":"갈색 후드티","type":"top","color":"#423529","material":null,"warm":"warm","warmScore":4,
            "style":"street","water":false,"grip":false,"photo":"http://localhost:8080/uploads/9c1e....png","aiTagged":true},
   "ai":{"type":"상의","typeConfidence":0.96,"typeCandidates":[{"label":"상의","type":"top","score":0.96}],
         "subtype":"후드티","style":"스트릿","styleConfidence":0.7,"warmConfidence":0.8,
         "colors":[{"name":"갈색","hex":"#423529","ratio":0.93}],"detectorLabel":"jacket",
         "needsReview":false,"warnings":[]}}]}
```
- `box`: 사진 안 위치 [왼쪽, 위, 오른쪽, 아래], 0~1 비율. 한 벌 사진이면 `null`.

## 코디 추천

| 메서드 | 경로 | 로그인 | 설명 |
|---|---|---|---|
| POST | `/api/outfits/recommend` | O | 날씨·장소(·고정 옷·선호 스타일) → 내 옷장에서 조합 추천 |

요청:
```json
{"pinnedId":7,
 "weather":{"tempC":8,"feelsLikeC":5,"tempMinC":3,"tempMaxC":12,"sky":"clear","precipProb":0.1,"windMs":3},
 "place":"office","topK":3,"preferredStyles":["casual","street"]}
```
- `weather.tempC` 만 필수. Open-Meteo 값: 현재 기온 → `tempC`, 체감 → `feelsLikeC`, 최저·최고 → `tempMinC`·`tempMaxC`,
  강수확률 % ÷ 100 → `precipProb`, 풍속(m/s, 요청에 `wind_speed_unit=ms`) → `windMs`. 직접 입력이면 `tempC` = (최저+최고) ÷ 2.
- 추위 민감도는 프론트가 체감 온도에 더해서 `feelsLikeC` 로 보낸다 (예: 체감 5, 추위 많이 탐 −3 → 2).
- `pinnedId` 생략 가능. 없으면 서버가 날씨에 맞는 상의 최대 5벌을 차례로 고정해 보고 점수가 높은 조합을 고른다 (`autoPinned: true`).
- `preferredStyles` 를 넣으면 그 스타일 옷이 많은 조합을 앞으로 올리고 근거에 "취향"이 붙는다.
- `place` 기본 `daily`, `sky` 기본 `clear`, `topK` 1~5 기본 3.

응답:
```json
{"apparentTempC":6.8,"effectiveTempC":6.8,"autoPinned":false,"warnings":[],
 "recommendations":[{"rank":1,"score":85.0,"reason":"체감 7°C라 카멜 울 코트를 걸쳤고, ...",
   "basis":[{"kind":"날씨","text":"기온 8°C, 체감 7°C, 맑음"},{"kind":"취향","text":"좋아하는 캐주얼 스타일이 들어간 조합을 우선했어요."}],
   "breakdown":{"보온":0.84,"색":0.94},
   "items":[{"slot":"상의","id":3,"name":"크림 니트","type":"top","color":"#f3ecd9","style":"formal",
             "photo":null,"pinned":true}]}]}
```
- `items` 순서: 상의 → 하의 → 겉옷 → 신발. `pinned: true` 가 고정된 옷.
- 400 `EMPTY_CLOSET`(옷장이 비었음), 404 `CLOTHES_NOT_FOUND`(고정 옷이 내 옷장에 없음), 503 `AI_UNAVAILABLE`.

## 에러 형식

```json
{"code":"VALIDATION_FAILED","message":"입력값을 확인해 주세요.","fieldErrors":{"color":"색상은 #RRGGBB 형식으로 보내 주세요."}}
```
- `message` 는 사용자에게 그대로 보여 줘도 되는 한글 문장. 프론트는 `code` 로 분기.
- 없는 값(예: `"style":"minimal"`, `"place":"cafe"`)이나 JSON 문법 오류는 400 `INVALID_REQUEST`.
- 코드 목록: `backend/src/main/java/com/ondo/closet/global/error/ErrorCode.java`

## 예정 (형식 확정 후 추가)

- `POST /api/feedback` 추천 거절 이유·착용 후 체감 기록 (AI 추천에 반영)
- 옷 상태(세탁·건조·수선)·즐겨찾기: 팀 결정 후
