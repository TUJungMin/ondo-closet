package com.ondo.closet.clothes;

/** 옷 한 벌의 속성 묶음. 요청 DTO, 샘플 옷장 JSON, (나중에) AI 태깅 결과가 모두 이 형식으로 들어온다. */
public record ClothesSpec(
        String name,
        Category category,
        String color,
        String material,
        int warmth,
        Style style,
        boolean waterproof,
        boolean grip,
        String imageUrl,
        boolean aiTagged
) {
}
