"""추천 이유 문장을 만들 때 쓰는 한국어 조사 처리."""

from __future__ import annotations

_HANGUL_BASE = 0xAC00
_HANGUL_END = 0xD7A3
_RIEUL = 8  # 종성 ㄹ
# 숫자를 한글로 읽었을 때 받침이 있는 것: 0(영) 1(일) 3(삼) 6(육) 7(칠) 8(팔)
_DIGIT_BATCHIM = {"0": 21, "1": _RIEUL, "3": 16, "6": 1, "7": _RIEUL, "8": _RIEUL}


def _jongseong(word: str) -> int:
    """마지막 글자의 종성 번호. 받침이 없으면 0."""
    for ch in reversed(word.strip()):
        if _HANGUL_BASE <= ord(ch) <= _HANGUL_END:
            return (ord(ch) - _HANGUL_BASE) % 28
        if ch.isdigit():
            return _DIGIT_BATCHIM.get(ch, 0)
        if ch.isalpha():
            return 4 if ch.lower() in "lmn" else 0
    return 0


def josa(word: str, pair: str) -> str:
    """``josa("니트", "을/를") -> "니트를"``. pair는 '받침 있음/받침 없음' 순서."""
    with_batchim, without = pair.split("/")
    jong = _jongseong(word)
    if with_batchim == "으로":  # ㄹ 받침은 '로'
        return word + (without if jong in (0, _RIEUL) else with_batchim)
    return word + (with_batchim if jong else without)
