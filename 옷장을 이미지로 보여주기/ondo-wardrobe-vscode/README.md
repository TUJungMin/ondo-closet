# 온도옷장 프론트엔드

날씨 기반 코디 추천, 내 옷장, 옷 등록, 캘린더 화면을 구현한 React 프론트엔드입니다.

## 사용 기술

- **TypeScript**: JavaScript에 타입 검사를 추가한 언어
- **React 19**: 화면과 사용자 상호작용 구성
- **Vite 8**: 개발 서버와 프로덕션 빌드
- **Tailwind CSS 4 + CSS**: 화면 스타일
- **pnpm**: 패키지 관리

Java나 Python 코드가 아니라 브라우저에서 실행되는 프론트엔드 코드입니다.

## VS Code에서 실행하기

### 준비

1. [Node.js 22](https://nodejs.org/)를 설치합니다.
2. 터미널에서 pnpm을 설치합니다.

```bash
npm install -g pnpm
```

### 실행

```bash
pnpm install
pnpm dev
```

터미널에 표시되는 로컬 주소를 브라우저에서 열면 됩니다.

프로덕션 빌드는 다음 명령으로 확인할 수 있습니다.

```bash
pnpm build
```

## 주요 파일

```text
.
├── public/
│   └── assets/          # 옷장, 날씨 배경, 의류 이미지
├── src/
│   ├── App.tsx          # 전체 화면과 상호작용
│   ├── index.css        # 전체 스타일과 반응형 디자인
│   └── main.tsx         # React 시작점
├── index.html           # HTML 시작 파일
├── package.json         # 실행 명령과 라이브러리
├── pnpm-lock.yaml       # 정확한 라이브러리 버전
├── tsconfig.json        # TypeScript 설정
└── vite.config.ts       # Vite 설정
```

## 현재 데이터 동작

현재 옷 등록 데이터는 React 메모리에만 저장됩니다. 페이지를 새로고침하면 등록한 옷이 초기화됩니다.

데이터를 영구 저장하려면 별도의 백엔드와 데이터베이스를 연결해야 합니다.

## Java 또는 Python과 연동하기

프론트엔드 코드를 Java나 Python에 그대로 붙여서 실행할 수는 없습니다. 실행 환경이 서로 다릅니다.

대신 다음 구조로 바로 연동할 수 있습니다.

```text
React 프론트엔드
      ↓ HTTP / JSON API
Java 또는 Python 백엔드
      ↓
데이터베이스 / 이미지 저장소
```

### Java

- Spring Boot로 REST API를 만듭니다.
- React에서 `fetch()`로 API를 호출합니다.
- 프로덕션에서는 React 빌드 결과인 `dist/`를 Spring Boot 정적 파일로 제공할 수도 있습니다.

### Python

- FastAPI, Flask 또는 Django로 REST API를 만듭니다.
- React에서 `fetch()`로 API를 호출합니다.
- 이미지 분석 기능이 필요하면 Python 서버에서 모델을 실행하고 분석 결과를 JSON으로 반환할 수 있습니다.

예를 들어 옷을 등록할 때 프론트엔드에서 다음 API를 호출하는 방식입니다.

```ts
const formData = new FormData()
formData.append('image', file)
formData.append('category', 'top')

await fetch('http://localhost:8000/api/clothes', {
  method: 'POST',
  body: formData,
})
```

Java와 Python 중 어떤 언어를 사용해도 프론트엔드는 그대로 유지할 수 있습니다. API 주소와 응답 형식만 맞추면 됩니다.
