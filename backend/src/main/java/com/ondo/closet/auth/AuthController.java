package com.ondo.closet.auth;

import com.ondo.closet.auth.dto.LoginRequest;
import com.ondo.closet.auth.dto.MeResponse;
import com.ondo.closet.auth.dto.SignupRequest;
import com.ondo.closet.auth.dto.TokenResponse;
import com.ondo.closet.global.security.AuthUser;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/api/auth/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public TokenResponse signup(@Valid @RequestBody SignupRequest request) {
        return authService.signup(request);
    }

    @PostMapping("/api/auth/login")
    public TokenResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    @PostMapping("/api/auth/guest")
    @ResponseStatus(HttpStatus.CREATED)
    public TokenResponse guest() {
        return authService.guest();
    }

    @GetMapping("/api/me")
    public MeResponse me(@AuthenticationPrincipal AuthUser user) {
        return authService.me(user.userId());
    }
}
