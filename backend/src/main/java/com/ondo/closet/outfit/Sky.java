package com.ondo.closet.outfit;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import com.ondo.closet.global.json.LowercaseEnums;

/** 하늘 상태. AI 서버(schemas.py Sky)와 같다. JSON 값은 소문자 (AL-10) */
public enum Sky {
    CLEAR("맑음"),
    CLOUDY("흐림"),
    RAIN("비"),
    SNOW("눈");

    private final String korean;

    Sky(String korean) {
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
    public static Sky from(String value) {
        return LowercaseEnums.parse(Sky.class, value);
    }
}
