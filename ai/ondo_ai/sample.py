"""추천 엔진 확인용 가을 옷장 예시 (글자 정보만, 사진 없음).

테스트와 `ondo-ai demo`에서 쓴다. 실제 시드 데이터(직접 찍은 사진 30벌 안팎)를 대신하지 않는다.
"""

from __future__ import annotations

from .schemas import Category, Garment, Status, Style

_T, _P, _S, _O, _F = Category.TOP, Category.PANTS, Category.SKIRT, Category.OUTER, Category.SHOES
_CA, _FO, _SP, _ST, _FE = Style.CASUAL, Style.FORMAL, Style.SPORTY, Style.STREET, Style.FEMININE

# (id, 이름, 종류, 색, 보온성, 스타일, 추가 속성)
_ROWS = [
    (1, "흰색 긴팔 티셔츠", _T, ["흰색"], 2, _CA, {}),
    (2, "베이지 니트", _T, ["베이지"], 4, _CA, {"favorite": True}),
    (3, "하늘색 셔츠", _T, ["하늘색"], 2, _FO, {}),
    (4, "회색 맨투맨", _T, ["회색"], 3, _CA, {"status": Status.DRYING}),
    (5, "검정 후드티", _T, ["검정"], 4, _ST, {}),
    (6, "버건디 니트", _T, ["버건디"], 4, _CA, {}),
    (7, "아이보리 블라우스", _T, ["아이보리"], 2, _FE, {}),
    (8, "남색 줄무늬 티셔츠", _T, ["남색", "흰색"], 2, _CA, {"status": Status.LAUNDRY}),
    (9, "진청 청바지", _P, ["남색"], 3, _CA, {"favorite": True}),
    (10, "검정 슬랙스", _P, ["검정"], 3, _FO, {}),
    (11, "베이지 면바지", _P, ["베이지"], 3, _CA, {}),
    (12, "카키 카고 팬츠", _P, ["카키"], 3, _ST, {}),
    (13, "갈색 코듀로이 팬츠", _P, ["갈색"], 4, _CA, {}),
    (14, "회색 조거 팬츠", _P, ["회색"], 3, _SP, {}),
    (15, "검정 플리츠 스커트", _S, ["검정"], 2, _FE, {}),
    (16, "베이지 롱 스커트", _S, ["베이지"], 2, _FE, {"status": Status.REPAIR}),
    (17, "베이지 트렌치코트", _O, ["베이지"], 3, _FO, {"favorite": True}),
    (18, "남색 블레이저", _O, ["남색"], 2, _FO, {}),
    (19, "회색 카디건", _O, ["회색"], 2, _CA, {}),
    (20, "검정 가죽 자켓", _O, ["검정"], 3, _ST, {}),
    (21, "카키 야상", _O, ["카키"], 3, _CA, {}),
    (22, "남색 바람막이", _O, ["남색"], 2, _SP, {"waterproof": True}),
    (23, "카멜 코트", _O, ["카멜"], 4, _FO, {}),
    (24, "검정 패딩", _O, ["검정"], 5, _CA, {}),
    (25, "흰색 스니커즈", _F, ["흰색"], 3, _CA, {"grip": True, "favorite": True}),
    (26, "검정 로퍼", _F, ["검정"], 3, _FO, {}),
    (27, "갈색 첼시부츠", _F, ["갈색"], 4, _CA, {"grip": True, "waterproof": True}),
    (28, "회색 러닝화", _F, ["회색"], 3, _SP, {"grip": True}),
    (29, "검정 레인부츠", _F, ["검정"], 3, _CA, {"grip": True, "waterproof": True}),
    (30, "베이지 플랫슈즈", _F, ["베이지"], 2, _FE, {}),
]


def autumn_wardrobe() -> list[Garment]:
    return [
        Garment(id=i, name=name, category=category, colors=colors, warmth=warmth, style=style, **extra)
        for i, name, category, colors, warmth, style, extra in _ROWS
    ]
