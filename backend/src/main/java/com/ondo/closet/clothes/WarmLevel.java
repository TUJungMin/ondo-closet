package com.ondo.closet.clothes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import com.ondo.closet.global.json.LowercaseEnums;

/**
 * 화면에서 쓰는 보온성 3단계: light · medium · warm (AL-03).
 * DB 와 AI 는 1~5 를 쓴다. light=2, medium=3, warm=4 로 저장하고, 1·5 는 각각 light·warm 으로 보인다.
 */
public enum WarmLevel {
    LIGHT(2),
    MEDIUM(3),
    WARM(4);

    private final int score;

    WarmLevel(int score) {
        this.score = score;
    }

    /** 이 단계를 1~5 로 저장할 때의 기본값 */
    public int score() {
        return score;
    }

    public static WarmLevel of(int score) {
        if (score <= 2) {
            return LIGHT;
        }
        return score == 3 ? MEDIUM : WARM;
    }

    /**
     * 저장할 1~5 값을 정한다. 세부값(1~5)이 같은 단계면 그대로 지켜서
     * AI가 붙인 패딩(5)·민소매(1) 같은 끝값이 단계 선택 한 번에 사라지지 않게 한다.
     */
    public int resolve(Integer detail) {
        return detail != null && detail >= 1 && detail <= 5 && of(detail) == this ? detail : score;
    }

    @JsonValue
    public String value() {
        return LowercaseEnums.value(this);
    }

    @JsonCreator
    public static WarmLevel from(String value) {
        return LowercaseEnums.parse(WarmLevel.class, value);
    }
}
