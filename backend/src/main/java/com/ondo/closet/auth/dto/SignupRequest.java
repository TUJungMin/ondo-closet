package com.ondo.closet.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** 개인정보 최소 수집: 이메일·실명 없이 아이디/비밀번호/닉네임만 받는다 */
public record SignupRequest(
        @NotBlank(message = "아이디를 입력해 주세요.")
        @Pattern(regexp = "^[a-zA-Z0-9_]{4,20}$", message = "아이디는 영문, 숫자, _ 조합 4~20자입니다.")
        String loginId,

        @NotBlank(message = "비밀번호를 입력해 주세요.")
        @Size(min = 8, max = 64, message = "비밀번호는 8~64자입니다.")
        String password,

        @NotBlank(message = "닉네임을 입력해 주세요.")
        @Size(max = 20, message = "닉네임은 20자 이하입니다.")
        String nickname
) {
}
