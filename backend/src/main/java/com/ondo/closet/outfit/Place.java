package com.ondo.closet.outfit;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import com.ondo.closet.global.json.LowercaseEnums;

/** 오늘 가는 곳. AI 서버(schemas.py Place)와 같은 6개, JSON 값은 소문자 (AL-09) */
public enum Place {
    DAILY("일상"),
    OFFICE("출근"),
    FORMAL("격식"),
    DATE("데이트"),
    OUTDOOR("야외활동"),
    SPORT("운동");

    private final String korean;

    Place(String korean) {
        this.korean = korean;
    }

    public String korean() {
        return korean;
    }

    @JsonValue
    public String value() {
        return LowercaseEnums.value(this);
    }

    @JsonCreator
    public static Place from(String value) {
        return LowercaseEnums.parse(Place.class, value);
    }
}
