package com.ondo.closet.global.error;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.Map;

/** 모든 에러 응답 형식: {"code":"...", "message":"...", "fieldErrors":{...}} */
@JsonInclude(JsonInclude.Include.NON_EMPTY)
public record ErrorResponse(String code, String message, Map<String, String> fieldErrors) {

    public static ErrorResponse of(ErrorCode code) {
        return new ErrorResponse(code.name(), code.message(), Map.of());
    }

    public static ErrorResponse of(ErrorCode code, Map<String, String> fieldErrors) {
        return new ErrorResponse(code.name(), code.message(), fieldErrors);
    }
}
