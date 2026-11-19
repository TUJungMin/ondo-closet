package com.ondo.closet.clothes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import com.ondo.closet.global.json.LowercaseEnums;

/** 스타일. AI(준호 님) 목록과 같은 5개, JSON 값은 소문자 (AL-04) */
public enum Style {
    CASUAL,   // 캐주얼
    FORMAL,   // 포멀
    SPORTY,   // 스포티
    STREET,   // 스트릿
    FEMININE; // 페미닌

    @JsonValue
    public String value() {
        return LowercaseEnums.value(this);
    }

    @JsonCreator
    public static Style from(String value) {
        return LowercaseEnums.parse(Style.class, value);
    }
}
