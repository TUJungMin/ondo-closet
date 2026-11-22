# 외부 자원 목록

대회 제출 별첨(외부 자원 출처, AI 활용내역)에 그대로 옮기는 문서다.
오픈소스·모델·데이터·API를 추가할 때마다 한 줄씩 적는다. (CLAUDE.md 3장 4항)

마지막 갱신: 2026-11-22 · 범위: AI 모듈(`ai/`). 백엔드·프론트에서 쓰는 자원은 각 담당이 아래에 이어서 적는다.

## 1. AI 모델

모두 서버 안에서 직접 실행한다. 외부 추론 API로 사진을 보내지 않는다. 가중치는 저장소에 넣지 않고 Hugging Face에서 내려받으며, 커밋 해시로 고정했다(`ai/ondo_ai/config.py`).

| 명칭 | 출처 | 라이선스 | 고정 리비전 | 사용 위치 | 용도 |
|---|---|---|---|---|---|
| Marqo/marqo-fashionSigLIP | https://huggingface.co/Marqo/marqo-fashionSigLIP | Apache-2.0 | `c56244cc94f9` | `ai/ondo_ai/vision/classifier.py` | 종류·세부 종류·보온성·스타일 제로샷 분류 (추가 학습 없음) |
| ZhengPeng7/BiRefNet | https://huggingface.co/ZhengPeng7/BiRefNet | MIT | `e2bf8e4460fc` | `ai/ondo_ai/vision/background.py` | 배경 제거 (옷 영역 마스크) |
| valentinafevu/yolos-fashionpedia | https://huggingface.co/valentinafevu/yolos-fashionpedia | MIT | `0cfdb77c01cf` | `ai/ondo_ai/vision/detect.py` | 옷이 여러 벌 찍힌 사진(착용 사진 등)에서 옷 위치 찾기 |
| patrickjohncyh/fashion-clip | https://huggingface.co/patrickjohncyh/fashion-clip | MIT | `7e3ba62ce16b` | `ai/ondo_ai/vision/classifier.py`, `ai/scripts/evaluate.py` | 평가 때 비교 기준선. 서비스에서는 쓰지 않음 |

- yolos-fashionpedia는 CLAUDE.md에 `valentinafeve/yolos-fashionpedia`로 적힌 모델이다. 저장소 주인의 계정명이 바뀌어 Hugging Face가 위 주소로 넘겨 준다(2026-11-18 확인). 가중치 파일은 2023-03-02 이후 바뀌지 않았다. 학습 데이터는 Fashionpedia(`detection-datasets/fashionpedia`, CC BY 4.0)이며 우리는 학습된 가중치만 쓴다. transformers에 들어 있는 YOLOS 구조라 원격 코드를 실행하지 않는다. 가중치가 `pytorch_model.bin` 형식뿐이라, 텐서만 읽는 방식(transformers 기본값)으로 불러온다.
- BiRefNet은 모델 저장소에 들어 있는 모델 정의 코드(`birefnet.py`)를 내려받아 실행한다(`trust_remote_code=True`). 고정한 리비전의 코드를 읽어 네트워크·프로세스 호출이 없음을 확인했다(2026-11-18).
- FashionSigLIP은 모델 카드가 안내하는 OpenCLIP 형식 가중치(`open_clip_model.safetensors`)를 쓴다. 저장소의 원격 코드는 실행하지 않는다.
- 색상 추출은 모델이 아니다. 배경을 지운 옷 픽셀을 k-means로 묶어 직접 계산한다(`ai/ondo_ai/vision/color.py`).

## 2. 오픈소스 라이브러리

버전은 2026-11-18 개발 PC에 설치된 값이다. 전체 고정 목록은 `ai/requirements.lock.txt`.

| 명칭 | 버전 | 출처 | 라이선스 | 사용 위치 |
|---|---|---|---|---|
| PyTorch | 2.11.0 (CUDA 12.8) | https://pytorch.org | BSD-3-Clause | 모델 실행 |
| torchvision | 0.26.0 | https://github.com/pytorch/vision | BSD-3-Clause | BiRefNet 모델 정의가 사용 |
| Transformers | 5.23.0 | https://github.com/huggingface/transformers | Apache-2.0 | BiRefNet·yolos-fashionpedia·fashion-clip 로드 |
| huggingface_hub | 2.4.0 | https://github.com/huggingface/huggingface_hub | Apache-2.0 | 모델 가중치 내려받기 |
| OpenCLIP (open_clip_torch) | 4.2.2 | https://github.com/mlfoundations/open_clip | MIT | FashionSigLIP 로드·추론 |
| timm | 1.0.31 | https://github.com/huggingface/pytorch-image-models | Apache-2.0 | 두 모델의 비전 백본 |
| Kornia | 0.9.2 | https://github.com/kornia/kornia | Apache-2.0 | BiRefNet 모델 정의가 사용 |
| einops | 0.8.2 | https://github.com/arogozhnikov/einops | MIT | BiRefNet 모델 정의가 사용 |
| safetensors | 0.8.0 | https://github.com/huggingface/safetensors | Apache-2.0 | 가중치 파일 읽기 |
| tokenizers | 0.23.3 | https://github.com/huggingface/tokenizers | Apache-2.0 | 후보 문구 토큰화 |
| SentencePiece | 0.2.3 | https://github.com/google/sentencepiece | Apache-2.0 | 후보 문구 토큰화 |
| ftfy | 6.3.1 | https://github.com/rspeer/python-ftfy | Apache-2.0 | 후보 문구 정리 (OpenCLIP 의존) |
| NumPy | 2.5.4 | https://numpy.org | BSD-3-Clause | 색상 계산 |
| Pillow | 13.0.0 | https://python-pillow.org | MIT-CMU | 사진 열기·크기 조정·배경 제거 이미지 저장 |
| Pydantic | 2.14.3 | https://github.com/pydantic/pydantic | MIT | 입출력 데이터 형식 |
| FastAPI | 0.163.2 | https://github.com/fastapi/fastapi | MIT | `ai/ondo_ai/service.py` (연결부) |
| Uvicorn | 0.54.0 | https://github.com/encode/uvicorn | BSD-3-Clause | 별도 추론 서버로 띄울 때 |
| python-multipart | 0.0.34 | https://github.com/Kludex/python-multipart | Apache-2.0 | 사진 업로드 받기 |
| pytest | 9.2.0 | https://docs.pytest.org | MIT | 테스트 (개발용) |
| HTTPX | 0.28.1 | https://github.com/encode/httpx | BSD-3-Clause | 서비스 테스트 (개발용) |

## 3. 참고한 공개 수식

코드를 가져온 것이 아니라 공개된 수식을 직접 구현했다.

| 명칭 | 출처 | 사용 위치 |
|---|---|---|
| CIEDE2000 색차식 | Sharma, Wu, Dalal, "The CIEDE2000 color-difference formula" (Color Research & Application, 2005). 논문의 검증 표 앞 세 쌍을 테스트 기준값으로 사용 | `ai/ondo_ai/vision/color.py`, `ai/tests/test_text_and_color.py` |
| 체감온도(wind chill) 식 | 미국 기상청·캐나다 환경부 2001년 공동 지수 | `ai/ondo_ai/recommend/thermal.py` |

기온별 보온 기준표, 색 조합 규칙, 장소·스타일 적합도 표는 외부 자료를 옮긴 것이 아니라 팀이 직접 정한 값이다.

## 4. 데이터

**저장소·서비스에 들어간 외부 데이터: 없음.**

- `ai/ondo_ai/sample.py`의 예시 옷장 30벌은 직접 작성한 글자 정보다(사진 없음).
- 시드 데이터용 옷 사진은 팀원이 직접 찍은 단품 사진을 쓴다. 준비되면 여기에 촬영자와 장수를 적는다.

**개발 중 동작 확인에만 쓴 사진 (저장소·서버에 넣지 않음)**

2026-11-18, 모델이 실제 사진에서 도는지 확인하려고 위키미디어 공용에서 이용 조건을 확인한 6장을 개발 PC 임시 폴더에 내려받아 썼다. 사람이 나온 사진은 없다. 모델 학습과 시드 데이터에는 쓰지 않았다. 다만 이 사진들에서 드러난 문제를 보고 색 이름 규칙을 고쳤으므로, 정식 정확도 평가에는 쓰지 않는다.

| 파일 | 출처 | 라이선스 |
|---|---|---|
| Jeans MET 1978.175.3 B.jpg | https://commons.wikimedia.org/wiki/File:Jeans_MET_1978.175.3_B.jpg | CC0 |
| Coat MET 1993.359 F.jpg | https://commons.wikimedia.org/wiki/File:Coat_MET_1993.359_F.jpg | CC0 |
| Woman's summer skirt from China, Honolulu Museum of Art 5152.1.JPG | https://commons.wikimedia.org/wiki/File:Woman%27s_summer_skirt_from_China,_Honolulu_Museum_of_Art_5152.1.JPG | CC0 |
| Keds basketball sneakers, 1929 - Bata Shoe Museum - DSC00724.JPG | https://commons.wikimedia.org/wiki/File:Keds_basketball_sneakers,_1929_-_Bata_Shoe_Museum_-_DSC00724.JPG | CC0 |
| Trenchcoat worn by President Gerald R. Ford.jpg | https://commons.wikimedia.org/wiki/File:Trenchcoat_worn_by_President_Gerald_R._Ford.jpg | Public domain |
| T-shirt.png | https://commons.wikimedia.org/wiki/File:T-shirt.png | CC0 |

2026-11-22 백엔드 연결 확인과 워밍업 시간 측정에는 외부 사진을 쓰지 않고, 코드로 그린 도형 그림 2장(티셔츠 모양, 상의·바지·신발 모양)을 개발 PC 임시 폴더에 만들어 썼다. 저장소에는 넣지 않았다.

여러 옷 사진 분석의 동작 확인에는 팀원이 대화 중에 제공한 착용 사진 1장을 썼다(얼굴 없음, 전신). 출처를 확인하지 못한 사진이라 저장소·서버·문서에 넣지 않았고 임시 폴더에서만 열었다. 모델 학습에는 쓰지 않았다. 이 사진에서 드러난 문제를 보고 색 이름 규칙과 옷 분리 규칙을 정했으므로 평가용으로는 쓸 수 없다. 정식 평가와 시연에는 팀이 직접 찍은 사진을 쓴다.

## 5. 외부 API

AI 모듈은 실행 중 외부 API를 부르지 않는다. (모델 가중치를 처음 한 번 Hugging Face에서 내려받는 것 제외)

- 날씨 정보 출처는 아직 정해지지 않았다(CLAUDE.md 9장). 정해지면 명칭·이용 조건을 여기에 적는다. 추천 엔진은 기온·체감·하늘 상태·강수확률·풍속을 값으로만 받으므로 어떤 출처든 연결할 수 있다.

## 6. 생성형 AI 활용

| 도구 | 활용 범위 | 시기 |
|---|---|---|
| Claude Code (Anthropic, 모델 Claude Fable 5.2) | `ai/` 폴더의 코드·테스트·스크립트와 `ai/docs/external-resources.md`, `ai/docs/eval.md` 초안 작성, 모델 로드·동작 확인 실행 | 2026-11-18 |
| Claude Code (Anthropic, 모델 Claude Fable 5.2) | 백엔드 연결 확인, 추천 시간 측정(`ai/scripts/bench_recommend.py`), 서버 시작 워밍업, 착용 사진 평가 기능(`ai/scripts/evaluate.py`), `ai/docs/ai-overview.md` 초안 | 2026-11-22 |

- 서비스 기능 자체에는 생성형 AI(LLM)를 쓰지 않는다. 추천 이유 문장은 규칙으로 만든 문장 틀이다.
