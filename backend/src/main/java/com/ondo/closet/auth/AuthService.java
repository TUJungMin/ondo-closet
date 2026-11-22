package com.ondo.closet.auth;

import com.ondo.closet.auth.dto.LoginRequest;
import com.ondo.closet.auth.dto.MeResponse;
import com.ondo.closet.auth.dto.SignupRequest;
import com.ondo.closet.auth.dto.TokenResponse;
import com.ondo.closet.demo.DemoClosetSeeder;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import com.ondo.closet.global.security.JwtTokenProvider;
import com.ondo.closet.user.User;
import com.ondo.closet.user.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.HexFormat;
import java.util.UUID;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final DemoClosetSeeder demoClosetSeeder;
    private final SecureRandom random = new SecureRandom();

    public AuthService(UserRepository userRepository, PasswordEncoder passwordEncoder,
                       JwtTokenProvider jwtTokenProvider, DemoClosetSeeder demoClosetSeeder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
        this.demoClosetSeeder = demoClosetSeeder;
    }

    @Transactional
    public TokenResponse signup(SignupRequest req) {
        if (req.loginId().toLowerCase().startsWith("guest_")) {
            // 게스트 계정 아이디 규칙과 겹치지 않게 막음
            throw new ApiException(ErrorCode.DUPLICATE_LOGIN_ID);
        }
        if (userRepository.existsByLoginId(req.loginId())) {
            throw new ApiException(ErrorCode.DUPLICATE_LOGIN_ID);
        }
        User user = userRepository.save(
                User.member(req.loginId(), passwordEncoder.encode(req.password()), req.nickname().trim()));
        return issue(user);
    }

    @Transactional(readOnly = true)
    public TokenResponse login(LoginRequest req) {
        User user = userRepository.findByLoginId(req.loginId())
                .filter(u -> !u.isGuest())
                .filter(u -> passwordEncoder.matches(req.password(), u.getPasswordHash()))
                // 아이디가 없는지 비밀번호가 틀렸는지 구분하지 않음 (계정 존재 여부 노출 방지)
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_CREDENTIALS));
        return issue(user);
    }

    /**
     * 심사위원·체험용: 매번 새 게스트 계정을 만들고 샘플 옷장을 채운 뒤 바로 로그인시킨다.
     * 공용 계정 하나를 쓰면 여러 사람이 서로의 데이터를 바꿀 수 있어서 계정을 분리한다.
     */
    @Transactional
    public TokenResponse guest() {
        String loginId = "guest_" + HexFormat.of().formatHex(randomBytes(5));
        String unusablePassword = passwordEncoder.encode(UUID.randomUUID().toString());
        User user = userRepository.save(User.guest(loginId, unusablePassword));
        demoClosetSeeder.seed(user);
        return issue(user);
    }

    @Transactional(readOnly = true)
    public MeResponse me(Long userId) {
        return userRepository.findById(userId)
                .map(MeResponse::from)
                .orElseThrow(() -> new ApiException(ErrorCode.USER_NOT_FOUND));
    }

    private TokenResponse issue(User user) {
        String token = jwtTokenProvider.createToken(user.getId());
        return TokenResponse.bearer(token, jwtTokenProvider.expiresInSeconds(), MeResponse.from(user));
    }

    private byte[] randomBytes(int n) {
        byte[] bytes = new byte[n];
        random.nextBytes(bytes);
        return bytes;
    }
}
