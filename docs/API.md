# API 문서

> 백엔드 담당: 곽정민 · 로컬 주소 `http://localhost:8080` · 배포 주소는 루트 README 참고
> API를 바꾸면 이 문서도 같은 PR에서 고쳐 주세요.


모든 응답은 JSON. 로그인이 필요한 API는 헤더에 `Authorization: Bearer <accessToken>`.

### 인증
| 메서드 | 경로 | 로그인 | 설명 |
|---|---|---|---|
| POST | `/api/auth/signup` | X | `{loginId, password, nickname}` → 토큰 |
| POST | `/api/auth/login` | X | `{loginId, password}` → 토큰 |
| POST | `/api/auth/guest` | X | **심사위원·체험용.** 새 게스트 계정 + 샘플 옷장 12벌 → 토큰 |
| GET | `/api/me` | O | 내 정보 |

토큰 응답 예시:
```json
{"accessToken":"eyJ...","tokenType":"Bearer","expiresIn":604800,
 "user":{"id":1,"loginId":"guest_3fa9c1d2e0","nickname":"게스트","guest":true,"warmthOffset":0}}
```

### 옷장
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/clothes` | 내 옷 전체 (`?category=OUTER` 로 필터) |
| GET | `/api/clothes/{id}` | 한 벌 조회 |
| POST | `/api/clothes` | 등록 |
| PUT | `/api/clothes/{id}` | 수정 (전체 필드) |
| DELETE | `/api/clothes/{id}` | 삭제 |
| POST | `/api/clothes/image` | 사진 업로드 (form-data `file`, JPG/PNG/WEBP, 15MB 이하) → `{"imageUrl":"/uploads/..."}` |

옷 데이터 형식 (AI 태깅 결과도 이 형식으로 맞추기):
```json
{"name":"카멜 울 코트","category":"OUTER","color":"카멜","material":"울","warmth":4,
 "style":"FORMAL","waterproof":false,"grip":false,"imageUrl":"/uploads/abc.jpg","aiTagged":true}
```
- `category`: `TOP` `PANTS` `SKIRT` `OUTER` `SHOES`
- `style`: `MINIMAL` `CASUAL` `FORMAL` `SPORTY`
- `warmth`: 1(아주 얇음) ~ 5(아주 따뜻함)

### AI 옷 분석 (준호 님 AI 서버와 연결)
| 메서드 | 경로 | 로그인 | 설명 |
|---|---|---|---|
| POST | `/api/clothes/analyze?mode=outfit` | O | 착용 사진(form-data `file`) → 상의·하의·겉옷·신발로 나눠 분석 |
| POST | `/api/clothes/analyze?mode=single` | O | 옷 한 벌 사진 분석 (기본값) |
| GET | `/api/ai/health` | X | `{"ai":"ok"}` 또는 `{"ai":"unavailable"}` |

- 백엔드가 AI 서버(`AI_SERVER_URL`, 기본 `http://127.0.0.1:8000`)를 대신 호출한다. 프론트는 AI 서버를 직접 부르지 않는다.
- **원본 사진은 저장하지 않고**, AI가 배경을 지운 옷 사진만 `/uploads/...png` 로 저장해 `draft.imageUrl` 에 넣는다.
- 각 `items[].draft` 는 `POST /api/clothes` 요청과 같은 모양이다. 사용자가 확인·수정한 뒤 그대로 보내면 저장된다.
- AI가 확신하지 못했거나 백엔드에 없는 값(스타일 `스트릿`·`페미닌`)은 `draft` 에서 `null`. 원래 값은 `ai` 에 남는다. `ai.needsReview=true` 면 화면에서 확인을 요청한다.
- AI 서버가 꺼져 있으면 503 `AI_UNAVAILABLE` → 화면은 직접 입력으로 넘어간다.

```json
{"mode":"outfit","elapsedMs":3120,"skipped":["가방"],"warnings":[],
 "items":[{"index":1,"box":[0.33,0.0,0.9,0.48],
   "draft":{"name":"갈색 후드티","category":"TOP","color":"갈색","material":null,"warmth":4,"style":null,
            "waterproof":false,"grip":false,"imageUrl":"/uploads/9c1e....png","aiTagged":true},
   "ai":{"category":"상의","categoryConfidence":0.96,"categoryCandidates":[{"label":"상의","category":"TOP","score":0.96}],
         "subtype":"후드티","style":"스트릿","styleConfidence":0.7,"warmthConfidence":0.8,
         "colors":[{"name":"갈색","hex":"#423529","ratio":0.93}],"detectorLabel":"jacket",
         "needsReview":true,"warnings":[]}}]}
```
- 확인용 화면: 백엔드 실행 후 `http://localhost:8080/ai-test.html`

### 에러 형식
```json
{"code":"VALIDATION_FAILED","message":"입력값을 확인해 주세요.","fieldErrors":{"warmth":"5 이하여야 합니다"}}
```
코드 목록은 `global/error/ErrorCode.java` 참고. 프론트는 `code` 로 분기.


## 예정 (형식은 확정 후 추가)

- `GET /api/weather` 시간대별 날씨
- `POST /api/outfits/recommend` 한 벌 고정 코디 추천
- `POST /api/outfits/{id}/feedback` 거절 이유·체감 기록
