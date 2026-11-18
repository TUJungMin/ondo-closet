package com.ondo.closet.global.error;

/** 서비스 계층에서 throw new ApiException(ErrorCode.XXX) 로 사용 */
public class ApiException extends RuntimeException {

    private final ErrorCode errorCode;

    public ApiException(ErrorCode errorCode) {
        super(errorCode.message());
        this.errorCode = errorCode;
    }

    public ErrorCode errorCode() {
        return errorCode;
    }
}
