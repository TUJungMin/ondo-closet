package com.ondo.closet.clothes.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Clothes;
import com.ondo.closet.clothes.Style;

import java.time.Instant;
import java.time.LocalDate;

public record ClothesResponse(
        Long id,
        String name,
        Category category,
        String color,
        String material,
        int warmth,
        Style style,
        boolean waterproof,
        boolean grip,
        String imageUrl,
        boolean aiTagged,
        LocalDate lastWornAt,
        Instant createdAt
) {
    public static ClothesResponse from(Clothes c) {
        return new ClothesResponse(c.getId(), c.getName(), c.getCategory(), c.getColor(), c.getMaterial(),
                c.getWarmth(), c.getStyle(), c.isWaterproof(), c.isGrip(), c.getImageUrl(), c.isAiTagged(),
                c.getLastWornAt(), c.getCreatedAt());
    }
}
