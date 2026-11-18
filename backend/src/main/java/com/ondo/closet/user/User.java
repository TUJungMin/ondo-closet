package com.ondo.closet.user;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "login_id", nullable = false, unique = true, length = 40)
    private String loginId;

    @Column(name = "password_hash", nullable = false, length = 100)
    private String passwordHash;

    @Column(nullable = false, length = 20)
    private String nickname;

    /** 심사위원·체험용 게스트 계정 여부 */
    @Column(nullable = false)
    private boolean guest;

    /** 체감온도 보정값. 추위를 많이 타면 +, 더위를 많이 타면 - (보온성 단계 기준) */
    @Column(name = "warmth_offset", nullable = false)
    private int warmthOffset;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    protected User() {
    }

    private User(String loginId, String passwordHash, String nickname, boolean guest) {
        this.loginId = loginId;
        this.passwordHash = passwordHash;
        this.nickname = nickname;
        this.guest = guest;
    }

    public static User member(String loginId, String passwordHash, String nickname) {
        return new User(loginId, passwordHash, nickname, false);
    }

    public static User guest(String loginId, String passwordHash) {
        return new User(loginId, passwordHash, "게스트", true);
    }

    @PrePersist
    void onCreate() {
        this.createdAt = Instant.now();
    }

    public void adjustWarmthOffset(int delta) {
        this.warmthOffset = Math.max(-2, Math.min(2, this.warmthOffset + delta));
    }

    public Long getId() {
        return id;
    }

    public String getLoginId() {
        return loginId;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public String getNickname() {
        return nickname;
    }

    public boolean isGuest() {
        return guest;
    }

    public int getWarmthOffset() {
        return warmthOffset;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
