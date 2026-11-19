package com.ondo.closet.global.json;

import java.util.Locale;

/**
 * 프론트와 주고받는 enum 값은 소문자다 (예: "top", "casual"). 받을 때는 대소문자를 가리지 않는다.
 * 각 enum 의 @JsonValue / @JsonCreator 에서 이 도우미를 쓴다.
 */
public final class LowercaseEnums {

    private LowercaseEnums() {
    }

    public static String value(Enum<?> e) {
        return e.name().toLowerCase(Locale.ROOT);
    }

    /** 없는 값이면 IllegalArgumentException → 컨트롤러에서 400 INVALID_REQUEST 로 응답 */
    public static <E extends Enum<E>> E parse(Class<E> type, String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Enum.valueOf(type, value.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("알 수 없는 값: " + value);
        }
    }
}
