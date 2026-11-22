# 온도옷장 (Ondo Closet)

날씨와 내 옷장을 함께 보고, 오늘 입을 코디를 추천하는 AI 서비스
2026 대한민국 청년 CAREER FAIR AI 해커톤 출품작

## 팀

| 이름 | 역할 | 폴더 |
|---|---|---|
| 김지명 | 기획·프론트·디자인·발표 | `ondo-wardrobe/` |
| 서준호 | AI 모델·추천 | `ai/` |
| 곽정민 | 백엔드·데이터 | `backend/` |

## 폴더 구조

```
ondo-closet/
├─ backend/        Spring Boot API 서버 (Java 21) · 8080
├─ ondo-wardrobe/  웹 화면 (HTML·JS, 빌드 없음) · 3000
├─ ai/             옷 사진 분석·코디 추천 추론 서버 (Python, FastAPI) · 8000
└─ docs/           API 문서
```

## 로컬 실행 방법 (프로토타입)

프로토타입은 PC 한 대에서 세 서버를 띄워 실행한다. 별도 배포 서버는 없다.

```
브라우저(3000) ──> 백엔드(8080) ──> AI 서버(8000)
```

준비물: Java 21, Python 3.11 또는 3.12. NVIDIA GPU가 있으면 사진 분석이 빠르다(없어도 동작).

**1. AI 서버** (`ai/` 폴더, 자세한 설치는 `ai/README.md`)

```bash
cd ai
python -m venv .venv && .venv/Scripts/activate          # macOS·Linux: source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128   # GPU 없으면 cu128 → cpu
pip install -r requirements.txt
uvicorn main:app --port 8000
```

처음 사진을 분석할 때 모델 가중치(약 1.3GB)를 내려받는다. 미리 올려 두려면 `ONDO_WARMUP=outfit` 환경 변수를 주고 띄운다.

**2. 백엔드** (`backend/` 폴더)

```bash
cd backend
./gradlew bootRun          # Windows CMD: gradlew.bat bootRun
```

설치 없이 메모리 DB(H2)로 뜬다. 서버를 끄면 계정·옷 정보가 사라진다. 연결 확인용 화면: http://localhost:8080/ai-test.html

**3. 프론트** (`ondo-wardrobe/` 폴더)

```bash
cd ondo-wardrobe
python -m http.server 3000
```

브라우저에서 http://localhost:3000 을 연다. (파일을 더블클릭해서 열면 서버 연결이 막힌다)
처음 화면에서 **게스트로 시작**을 누르면 샘플 옷 12벌이 든 계정으로 바로 체험할 수 있다.

API 형식: `docs/API.md`

## 향후 배포 계획

제출 프로토타입은 로컬 실행만 지원한다. 서비스로 공개할 때는 아래 순서로 배포한다.

| 항목 | 계획 |
|---|---|
| 서버 | 클라우드 서버 한 대(메모리 8GB, CPU)에 Docker Compose로 DB · AI 서버 · 백엔드 · 웹(nginx)을 함께 띄운다. 웹 주소 하나로 프론트와 `/api`를 묶는다 |
| DB | 로컬용 H2 대신 PostgreSQL 사용. 백엔드 `prod` 설정(환경 변수로 DB 주소·계정 주입)은 준비돼 있다 |
| AI 서버 | GPU 없는 서버에서는 `ONDO_DEVICE=cpu`, `ONDO_SEGMENT_SIZE=512`로 실행하고, `ONDO_WARMUP=outfit`으로 시작할 때 모델을 미리 올린다. 모델 가중치는 디스크에 보관해 재시작 때 다시 받지 않는다 |
| 사진 저장 | 처음에는 서버 디스크, 사용자가 늘면 객체 저장소(S3 등)로 옮긴다 |
| 보안 | 도메인 + HTTPS 적용, JWT 비밀키·DB 비밀번호는 환경 변수로만 관리, CORS는 배포 주소만 허용 |
| 확인 | 배포 서버에서 사진 분석 시간을 측정하고, 느리면 가벼운 배경 제거 방식으로 교체한다 (`ai/docs/eval.md`) |

## 작업 규칙

1. `main` 은 항상 실행 가능한 상태로 유지. 직접 push 하지 않고 PR로 합친다.
2. 브랜치 이름: `feat/기능`, `fix/버그`, `docs/문서` (예: `feat/clothes-api`)
3. 커밋 메시지: `feat: 옷 등록 API 추가`, `fix: 로그인 토큰 만료 처리` 처럼 앞에 종류를 붙인다.
4. **API 키·비밀번호는 절대 커밋하지 않는다.** 각 폴더의 `.env.example` 에 항목 이름만 적고, 실제 값은 로컬 `.env` 와 배포 플랫폼 환경변수에만 둔다.
5. 실제 개인정보·얼굴 사진은 외부 AI에 보내지 않는다 (대회 규칙). 시연 데이터는 옷 사진·가상 데이터만 사용.

## 일정

| 날짜 | 목표 |
|---|---|
| 11/18 (수) | 저장소·실행 환경 구성, 공통 데이터·API 형식 확정 |
| 11/19 (목) | AI 기본 모델 확정, 옷장 저장·조회 연결 |
| 11/20 (금) | 한 벌 고정 추천, 날씨·장소 반영 |
| 11/21 (토) | 피드백 반영, 배포, 오류 수정 |
| 11/22 (일) | 기능 동결, 제출 자료·시연 영상 완성 |
| 11/23 (월) 17:00 | 제출 마감 (링크 업로드 + 이메일 발송) |

## Credits / Licenses

외부 모델·데이터·오픈소스를 쓰면 여기에 이름 / 라이선스 / 링크 / 용도를 기록한다. (제출 시 소개서 별첨에도 동일하게 기재)

| 이름 | 라이선스 | 링크 | 용도 |
|---|---|---|---|
| Spring Boot | Apache-2.0 | https://spring.io/projects/spring-boot | 백엔드 프레임워크 |
| jjwt | Apache-2.0 | https://github.com/jwtk/jjwt | JWT 인증 |
| H2 Database | MPL-2.0 / EPL-1.0 | https://h2database.com | 로컬 실행용 DB |
| Marqo/marqo-fashionSigLIP | Apache-2.0 | https://huggingface.co/Marqo/marqo-fashionSigLIP | 옷 종류·보온성·스타일 분류 (추가 학습 없음) |
| ZhengPeng7/BiRefNet | MIT | https://huggingface.co/ZhengPeng7/BiRefNet | 옷 사진 배경 제거 |
| valentinafevu/yolos-fashionpedia | MIT | https://huggingface.co/valentinafevu/yolos-fashionpedia | 착용 사진에서 옷 위치 찾기 |
| Open-Meteo | CC BY 4.0 (데이터) | https://open-meteo.com | 날씨 예보 |

AI 쪽 라이브러리 전체 목록과 버전은 `ai/docs/external-resources.md`에 있다.
