"""제로샷 분류에 넣는 후보 문구.

문구는 영어로 주고 결과는 한글로 바꿔 저장한다. 정확도가 낮으면 모델 추가 학습보다
이 파일의 문구를 먼저 조정한다. (CLAUDE.md 6장)

세부 종류(Subtype)마다 기본 보온성·스타일·방수·접지 값을 붙여 두었다. AI 제안의 초안으로만 쓰고
사용자가 언제든 고칠 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas import Category, Style


@dataclass(frozen=True)
class Subtype:
    name: str  # 화면에 보이는 한글 이름
    prompt: str  # 모델에 넣는 영어 문구
    category: Category
    warmth: int  # 1(한여름용)~5(한겨울용)
    style: Style
    waterproof: bool = False
    grip: bool = False


_T, _P, _S, _O, _F = Category.TOP, Category.PANTS, Category.SKIRT, Category.OUTER, Category.SHOES
_CA, _FO, _SP, _ST, _FE = Style.CASUAL, Style.FORMAL, Style.SPORTY, Style.STREET, Style.FEMININE

SUBTYPES: tuple[Subtype, ...] = (
    # 상의
    Subtype("민소매", "a sleeveless top", _T, 1, _CA),
    Subtype("반팔 티셔츠", "a short sleeve t-shirt", _T, 1, _CA),
    Subtype("폴로 셔츠", "a polo shirt", _T, 1, _CA),
    Subtype("긴팔 티셔츠", "a long sleeve t-shirt", _T, 2, _CA),
    Subtype("셔츠", "a button-up shirt", _T, 2, _FO),
    Subtype("블라우스", "a blouse", _T, 2, _FE),
    Subtype("니트 조끼", "a knit vest", _T, 2, _CA),
    Subtype("맨투맨", "a sweatshirt", _T, 3, _CA),
    Subtype("후드티", "a hoodie", _T, 4, _ST),
    Subtype("니트", "a knit sweater", _T, 4, _CA),
    # 바지
    Subtype("반바지", "shorts", _P, 1, _CA),
    Subtype("레깅스", "leggings", _P, 2, _SP),
    Subtype("청바지", "jeans", _P, 3, _CA),
    Subtype("슬랙스", "dress pants", _P, 3, _FO),
    Subtype("면바지", "chino pants", _P, 3, _CA),
    Subtype("조거 팬츠", "jogger sweatpants", _P, 3, _SP),
    Subtype("카고 팬츠", "cargo pants", _P, 3, _ST),
    Subtype("코듀로이 팬츠", "corduroy pants", _P, 4, _CA),
    # 스커트
    Subtype("미니 스커트", "a mini skirt", _S, 1, _FE),
    Subtype("플리츠 스커트", "a pleated skirt", _S, 2, _FE),
    Subtype("롱 스커트", "a long skirt", _S, 2, _FE),
    Subtype("데님 스커트", "a denim skirt", _S, 2, _CA),
    # 겉옷
    Subtype("카디건", "a cardigan", _O, 2, _CA),
    Subtype("블레이저", "a blazer", _O, 2, _FO),
    Subtype("데님 자켓", "a denim jacket", _O, 2, _CA),
    Subtype("바람막이", "a windbreaker jacket", _O, 2, _SP, waterproof=True),
    Subtype("레인코트", "a raincoat", _O, 2, _CA, waterproof=True),
    Subtype("후드 집업", "a zip-up hoodie", _O, 3, _ST),
    Subtype("가죽 자켓", "a leather jacket", _O, 3, _ST),
    Subtype("항공 점퍼", "a bomber jacket", _O, 3, _ST),
    Subtype("야상", "a field jacket", _O, 3, _CA),
    Subtype("트렌치코트", "a trench coat", _O, 3, _FO),
    Subtype("패딩 조끼", "a puffer vest", _O, 3, _CA),
    Subtype("플리스", "a fleece jacket", _O, 4, _CA),
    Subtype("코트", "a wool coat", _O, 4, _FO),
    Subtype("패딩", "a puffer jacket", _O, 5, _CA),
    # 신발
    Subtype("샌들", "sandals", _F, 1, _CA),
    Subtype("슬리퍼", "slide slippers", _F, 1, _CA),
    Subtype("플랫슈즈", "ballet flats", _F, 2, _FE),
    Subtype("힐", "high heels", _F, 2, _FE),
    Subtype("스니커즈", "sneakers", _F, 3, _CA, grip=True),
    Subtype("러닝화", "running shoes", _F, 3, _SP, grip=True),
    Subtype("로퍼", "loafers", _F, 3, _FO),
    Subtype("구두", "dress shoes", _F, 3, _FO),
    Subtype("레인부츠", "rain boots", _F, 3, _CA, waterproof=True, grip=True),
    Subtype("부츠", "ankle boots", _F, 4, _CA, grip=True),
    Subtype("등산화", "hiking boots", _F, 4, _SP, waterproof=True, grip=True),
    Subtype("방한 부츠", "fur lined winter boots", _F, 5, _CA),
)

# 옷장 다섯 종류에 들지 않는 물건. 이쪽 확률이 가장 높으면 종류를 비워 둔다.
OTHER_ITEMS: tuple[tuple[str, str], ...] = (
    ("원피스", "a dress"),
    ("점프수트", "a jumpsuit"),
    ("가방", "a bag"),
    ("모자", "a hat"),
    ("목도리", "a scarf"),
    ("양말", "socks"),
    ("벨트", "a belt"),
    ("속옷", "underwear"),
)

SUBTYPE_PROMPTS: tuple[str, ...] = tuple(s.prompt for s in SUBTYPES) + tuple(p for _, p in OTHER_ITEMS)
SUBTYPE_BY_NAME: dict[str, Subtype] = {s.name: s for s in SUBTYPES}

# 보온성: 얇음 / 중간 / 두꺼움. 세부 종류의 기본값과 크게 어긋날 때만 한 단계 보정하는 데 쓴다.
WARMTH_PROMPTS: tuple[str, ...] = (
    "thin lightweight summer clothing",
    "mid-weight clothing for spring and autumn",
    "thick warm winter clothing",
)
WARMTH_LEVELS: tuple[int, ...] = (1, 3, 5)

STYLE_PROMPTS: tuple[tuple[Style, str], ...] = (
    (Style.CASUAL, "casual everyday clothing"),
    (Style.FORMAL, "formal business clothing"),
    (Style.SPORTY, "athletic sportswear"),
    (Style.STREET, "streetwear fashion"),
    (Style.FEMININE, "feminine romantic clothing"),
)
