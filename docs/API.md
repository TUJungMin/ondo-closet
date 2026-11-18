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
| POST | `/api/clothes/image` | 사진 업로드 (form-data `file`, JPG/PNG/WEBP, 5MB 이하) → `{"imageUrl":"/uploads/..."}` |

옷 데이터 형식 (AI 태깅 결과도 이 형식으로 맞추기):
```json
{"name":"카멜 울 코트","category":"OUTER","color":"카멜","material":"울","warmth":4,
 "style":"FORMAL","waterproof":false,"grip":false,"imageUrl":"/uploads/abc.jpg","aiTagged":true}
```
- `category`: `TOP` `PANTS` `SKIRT` `OUTER` `SHOES`
- `style`: `MINIMAL` `CASUAL` `FORMAL` `SPORTY`
- `warmth`: 1(아주 얇음) ~ 5(아주 따뜻함)

### 에러 형식
```json
{"code":"VALIDATION_FAILED","message":"입력값을 확인해 주세요.","fieldErrors":{"warmth":"5 이하여야 합니다"}}
```
코드 목록은 `global/error/ErrorCode.java` 참고. 프론트는 `code` 로 분기.


## 예정 (형식은 확정 후 추가)

- `GET /api/weather` 시간대별 날씨
- `POST /api/clothes/tag` 사진 → AI 종류·색상 제안
- `POST /api/outfits/recommend` 한 벌 고정 코디 추천
- `POST /api/outfits/{id}/feedback` 거절 이유·체감 기록
