package com.ondo.closet.auth.dto;

import com.ondo.closet.user.User;

public record MeResponse(Long id, String loginId, String nickname, boolean guest, int warmthOffset) {

    public static MeResponse from(User user) {
        return new MeResponse(user.getId(), user.getLoginId(), user.getNickname(), user.isGuest(),
                user.getWarmthOffset());
    }
}
