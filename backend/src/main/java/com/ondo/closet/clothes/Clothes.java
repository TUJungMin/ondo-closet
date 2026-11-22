package com.ondo.closet.clothes;

import com.ondo.closet.user.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.Instant;
import java.time.LocalDate;

@Entity
@Table(name = "clothes", indexes = @Index(name = "idx_clothes_user", columnList = "user_id"))
public class Clothes {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, length = 60)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private Category category;

    /** #RRGGBB (AL-02). AI 에 보낼 때 가장 가까운 색 이름으로 바꾼다 */
    @Column(nullable = false, length = 30)
    private String color;

    @Column(length = 30)
    private String material;

    /** 보온성 1(아주 얇음) ~ 5(아주 따뜻함) */
    @Column(nullable = false)
    private int warmth;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private Style style;

    @Column(nullable = false)
    private boolean waterproof;

    /** 미끄럼 방지 (신발) */
    @Column(nullable = false)
    private boolean grip;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    /** AI 자동 태깅으로 채운 값인지 (사용자가 확인·수정하면 그대로 true 유지, 소개서의 AI 활용 근거로 사용) */
    @Column(name = "ai_tagged", nullable = false)
    private boolean aiTagged;

    @Column(name = "last_worn_at")
    private LocalDate lastWornAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected Clothes() {
    }

    public Clothes(User user, ClothesSpec spec) {
        this.user = user;
        apply(spec);
    }

    public void apply(ClothesSpec spec) {
        this.name = spec.name().trim();
        this.category = spec.category();
        this.color = spec.color().trim().toLowerCase();
        this.material = spec.material() == null || spec.material().isBlank() ? null : spec.material().trim();
        this.warmth = spec.warmth();
        this.style = spec.style();
        this.waterproof = spec.waterproof();
        this.grip = spec.grip();
        this.imageUrl = spec.imageUrl();
        this.aiTagged = spec.aiTagged();
    }

    public void markWorn(LocalDate date) {
        this.lastWornAt = date;
    }

    @PrePersist
    void onCreate() {
        this.createdAt = Instant.now();
        this.updatedAt = this.createdAt;
    }

    @PreUpdate
    void onUpdate() {
        this.updatedAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public User getUser() {
        return user;
    }

    public String getName() {
        return name;
    }

    public Category getCategory() {
        return category;
    }

    public String getColor() {
        return color;
    }

    public String getMaterial() {
        return material;
    }

    public int getWarmth() {
        return warmth;
    }

    public Style getStyle() {
        return style;
    }

    public boolean isWaterproof() {
        return waterproof;
    }

    public boolean isGrip() {
        return grip;
    }

    public String getImageUrl() {
        return imageUrl;
    }

    public boolean isAiTagged() {
        return aiTagged;
    }

    public LocalDate getLastWornAt() {
        return lastWornAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
