# frontend (담당: 김지명)

웹 화면. 프레임워크와 Node 버전이 정해지면 아래를 채워 주세요.

- 프레임워크:
- Node 버전:
- 실행 방법:
  ```bash
  npm install
  npm run dev
  ```

## 백엔드 연결

- 로컬 API 주소: `http://localhost:8080`
- API 목록과 요청·응답 예시: [`docs/API.md`](../docs/API.md)
- 로그인 후 받은 `accessToken` 을 모든 요청 헤더에 `Authorization: Bearer <accessToken>` 으로 붙입니다.
- 심사위원용 "체험하기" 버튼은 `POST /api/auth/guest` 를 호출하면 됩니다 (샘플 옷장이 채워진 새 계정).
- 에러 응답은 `{"code","message"}` 형식. 화면 분기는 `code` 로 하세요.

## 환경변수

`.env.example` 을 복사해서 `.env` 로 만들고 값을 채웁니다. `.env` 는 커밋하지 않습니다.
