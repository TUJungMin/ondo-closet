package com.ondo.closet.auth.dto;

/** 프론트는 accessToken을 저장해 두고 이후 요청에 Authorization: Bearer <accessToken> 헤더로 보낸다 */
public record TokenResponse(String accessToken, String tokenType, long expiresIn, MeResponse user) {

    public static TokenResponse bearer(String token, long expiresIn, MeResponse user) {
        return new TokenResponse(token, "Bearer", expiresIn, user);
    }
}
