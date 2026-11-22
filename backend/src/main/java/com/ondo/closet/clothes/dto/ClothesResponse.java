package com.ondo.closet.clothes.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Clothes;
import com.ondo.closet.clothes.Style;
import com.ondo.closet.clothes.WarmLevel;
import com.ondo.closet.image.PhotoService;

import java.time.Instant;
import java.time.LocalDate;

/** 옷 응답. 필드 이름은 프론트 기준 (AL-05) */
public record ClothesResponse(
        Long id,
        String name,
        Category type,
        String color,          // #RRGGBB
        String material,
        WarmLevel warm,        // light · medium · warm
        int warmScore,         // 1~5 세부값 (추천 엔진이 쓰는 값)
        Style style,
        boolean water,
        boolean grip,
        String photo,          // 전체 주소. 없으면 null
        boolean aiTagged,
        LocalDate lastWorn,
        Instant createdAt
) {
    public static ClothesResponse from(Clothes c, PhotoService photos) {
        return new ClothesResponse(c.getId(), c.getName(), c.getCategory(), c.getColor(), c.getMaterial(),
                WarmLevel.of(c.getWarmth()), c.getWarmth(), c.getStyle(), c.isWaterproof(), c.isGrip(),
                photos.publicUrl(c.getImageUrl()), c.isAiTagged(), c.getLastWornAt(), c.getCreatedAt());
    }
}
