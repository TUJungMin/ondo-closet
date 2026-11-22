# 온도옷장 백엔드 (ondo-closet-backend)

Spring Boot 3.5 · Java 21 · JPA · Spring Security(JWT) · PostgreSQL(배포) / H2(로컬)

## 1. 처음 실행하기

```bash
# 테스트 먼저 (가입·로그인·게스트·옷장 CRUD·이미지 업로드 흐름 검증)
./gradlew test

# 로컬 서버 실행 (H2 메모리 DB, 설치 필요 없음 · 끄면 데이터 초기화)
./gradlew bootRun
```

- IntelliJ: `File > Open` 으로 폴더를 열면 Gradle 프로젝트로 인식됩니다. JDK 21을 지정하세요.
- 동작 확인: http://localhost:8080/api/health → `{"status":"ok"}`

## 2. 환경변수

| 이름 | 로컬 | 배포(prod) | 설명 |
|---|---|---|---|
| `SPRING_PROFILES_ACTIVE` | (생략=local) | `prod` | Dockerfile에 이미 prod로 지정됨 |
| `JWT_SECRET` | 기본값 있음 | **필수** | 32자 이상 무작위 문자열 |
| `DATABASE_URL` | - | **필수** | `jdbc:postgresql://<host>/<db>?sslmode=require` |
| `DATABASE_USERNAME` / `DATABASE_PASSWORD` | - | **필수** | |
| `CORS_ALLOWED_ORIGINS` | localhost 몇 개 | **필수** | 프론트 주소, 쉼표 구분 |
| `PORT` | 8080 | 호스팅이 지정 | |
| `STORAGE_DIR` | `./uploads` | 선택 | 로컬 이미지 저장 폴더 |

> API 키·비밀번호는 절대 Git에 올리지 마세요. 호스팅 서비스의 환경변수 설정에 넣습니다.

## 3. API

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

## 4. 구조

```
com.ondo.closet
├─ auth/        가입·로그인·게스트 로그인
├─ user/        User 엔티티
├─ clothes/     옷장 CRUD (Clothes 엔티티, Category, Style)
├─ image/       사진 업로드 (ImageStorage 인터페이스 + 로컬 구현)
├─ demo/        게스트용 샘플 옷장 (resources/demo/demo-closet.json)
├─ health/      /api/health
└─ global/      설정(Security, CORS), JWT, 공통 에러 처리
```

## 5. 배포 (Docker)

```bash
docker build -t ondo-backend .
docker run -p 8080:8080 -e JWT_SECRET=... -e DATABASE_URL=... -e DATABASE_USERNAME=... \
  -e DATABASE_PASSWORD=... -e CORS_ALLOWED_ORIGINS=https://<프론트주소> ondo-backend
```
Dockerfile을 지원하는 호스팅(Render, Railway, Fly.io 등)에 그대로 올릴 수 있습니다.

배포 전 체크:
- [ ] 무료 플랜은 일정 시간 요청이 없으면 서버가 잠들 수 있음 → 시연 전에 `/api/health` 호출로 깨우기
- [ ] 무료 플랜 디스크는 재배포 시 초기화될 수 있음 → `ImageStorage` 를 오브젝트 스토리지 구현으로 교체
- [ ] 12/7 본선까지 DB·서버·AI API 크레딧이 유지되는지 확인

## 6. 다음 작업

1. 날씨 API (`GET /api/weather`, Open-Meteo 시간대별 예보 + 캐싱)
2. 조합 계산 엔진 (유효한 코디 규칙 → 추천 후보, 구매 시 새 조합 수) + 단위 테스트
3. AI 태깅 (`POST /api/clothes/tag`) · 추천 · 구매 제안 · 채팅 에이전트
4. 체감 피드백 (`User.warmthOffset` 조정 API)
5. 오래된 게스트 계정 정리 (예: 7일 지난 guest 삭제 스케줄러)
