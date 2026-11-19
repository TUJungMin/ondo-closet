package com.ondo.closet.clothes;

/**
 * 옷 한 벌의 속성 묶음 (내부용). 요청 DTO, 샘플 옷장 JSON 이 이 형식으로 바뀌어 엔티티에 들어간다.
 * warmth 는 1~5, imageUrl 은 "/uploads/..." 처럼 서버 안의 경로다.
 */
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
