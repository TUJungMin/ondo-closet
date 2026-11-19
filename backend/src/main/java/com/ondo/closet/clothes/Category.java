package com.ondo.closet.clothes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import com.ondo.closet.global.json.LowercaseEnums;

/**
 * 옷 종류. JSON 값은 소문자: top · pants · skirt · outer · shoes (AL-01).
 * 코디 조합에서 PANTS와 SKIRT는 둘 다 '하의'로 취급한다.
 */
public enum Category {
    TOP,     // 상의
    PANTS,   // 바지
    SKIRT,   // 스커트
    OUTER,   // 겉옷
    SHOES;   // 신발

    public boolean isBottom() {
        return this == PANTS || this == SKIRT;
    }

    @JsonValue
    public String value() {
        return LowercaseEnums.value(this);
    }

    @JsonCreator
    public static Category from(String value) {
        return LowercaseEnums.parse(Category.class, value);
    }
}
