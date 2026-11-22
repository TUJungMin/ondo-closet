package com.ondo.closet.global.security;

/**
 * 로그인한 사용자 정보. 컨트롤러에서 @AuthenticationPrincipal AuthUser user 로 받는다.
 */
public record AuthUser(Long userId) {
}
