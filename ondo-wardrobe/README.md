# 온도옷장 프론트

현재 화면은 `ondo-wardrobe-weather.html`이며 `index.html`에서 이 화면으로 이동합니다.
별도 빌드 없이 이 폴더에서 다음 명령을 실행하고 http://localhost:3000 을 엽니다.

```sh
python -m http.server 3000
```

백엔드는 Java 21 기반 Spring Boot로 http://localhost:8080 에서 실행합니다.
AI 분석과 추천도 프론트에서 백엔드 8080에 요청하며, 백엔드가 AI 서버에 연결합니다.
백엔드 CORS 설정에는 실제 프론트 주소가 등록되어 있어야 합니다.

- `assets/js/server-api.js` — API 주소, 토큰, JSON·파일 전송, 오류 처리
- `assets/js/server-ui.js` — 인증·게스트, 옷장 저장, AI 분석, 서버 추천 화면
- `assets/css/server-ui.css` — 기존 화면에 추가한 폼·상태 스타일

날씨는 Open-Meteo에서 자동 조회합니다. 추천 API는 날씨·장소·스타일을 받습니다.
프론트는 서버 후보 5개 중 최대 3개를 서버 점수와 선택한 컬러의 유사도를 함께 반영해 표시합니다.
AI가 배경을 제거한 사진은 분석 응답의 `draft.photo`를 저장하고, 추천 카드에 서버의 `items[].photo`를 사용합니다.
게스트 옷장의 12벌은 서버 사진이 비어 있을 때 `assets/img/sample-wardrobe.png`의 해당 예시 사진을 씁니다.
추천 조합 미리보기에는 해당 추천의 옷 사진과 이름이 표시됩니다. 미리 확인한 핀이 상의·하의와 맞을 때 Pinterest 착장 사진을 함께 표시합니다. 일치하는 핀이 없거나 사진을 불러오지 못하면 조합 이름으로 검색하는 링크를 제공합니다.
