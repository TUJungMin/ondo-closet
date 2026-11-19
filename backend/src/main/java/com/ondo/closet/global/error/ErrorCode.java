package com.ondo.closet.global.error;

import org.springframework.http.HttpStatus;

/** 프론트와 약속한 에러 코드. 화면에서는 code 값으로 분기하고 message는 그대로 보여줘도 된다. */
public enum ErrorCode {
    VALIDATION_FAILED(HttpStatus.BAD_REQUEST, "입력값을 확인해 주세요."),
    INVALID_REQUEST(HttpStatus.BAD_REQUEST, "요청 형식이 올바르지 않습니다."),
    INVALID_IMAGE(HttpStatus.BAD_REQUEST, "JPG, PNG, WEBP 이미지만 올릴 수 있습니다."),
    IMAGE_TOO_LARGE(HttpStatus.BAD_REQUEST, "이미지는 15MB 이하만 올릴 수 있습니다."),
    INVALID_PHOTO(HttpStatus.BAD_REQUEST, "사진은 JPG, PNG, WEBP 데이터나 이 서버에 올린 사진 주소로 보내 주세요."),
    PHOTO_TOO_LARGE(HttpStatus.BAD_REQUEST, "사진 데이터는 3MB 이하만 보낼 수 있어요. 사진을 줄여서 보내 주세요."),
    EMPTY_CLOSET(HttpStatus.BAD_REQUEST, "옷장에 옷을 먼저 등록해 주세요."),
    CLOSET_FULL(HttpStatus.BAD_REQUEST, "옷장에 더 이상 옷을 추가할 수 없습니다."),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다."),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "아이디 또는 비밀번호가 올바르지 않습니다."),
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."),
    CLOTHES_NOT_FOUND(HttpStatus.NOT_FOUND, "옷을 찾을 수 없습니다."),
    DUPLICATE_LOGIN_ID(HttpStatus.CONFLICT, "이미 사용 중인 아이디입니다."),
    AI_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "AI 분석 서버에 연결할 수 없어요. 옷 정보를 직접 입력해 주세요."),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");

    private final HttpStatus status;
    private final String message;

    ErrorCode(HttpStatus status, String message) {
        this.status = status;
        this.message = message;
    }

    public HttpStatus status() {
        return status;
    }

    public String message() {
        return message;
    }
}
