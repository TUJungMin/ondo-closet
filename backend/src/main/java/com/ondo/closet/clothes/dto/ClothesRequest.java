package com.ondo.closet.clothes.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.ClothesSpec;
import com.ondo.closet.clothes.Style;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * 옷 등록·수정 요청. category / style 은 대문자 enum 값으로 보낸다.
 * 예: {"name":"카멜 울 코트","category":"OUTER","color":"카멜","material":"울","warmth":4,
 *      "style":"FORMAL","waterproof":false,"grip":false,"imageUrl":"/uploads/abc.jpg","aiTagged":true}
 */
public record ClothesRequest(
        @NotBlank(message = "이름을 입력해 주세요.") @Size(max = 50) String name,
        @NotNull(message = "종류를 선택해 주세요.") Category category,
        @NotBlank(message = "색상을 입력해 주세요.") @Size(max = 30) String color,
        @Size(max = 30) String material,
        @NotNull(message = "보온성을 선택해 주세요.") @Min(1) @Max(5) Integer warmth,
        @NotNull(message = "스타일을 선택해 주세요.") Style style,
        Boolean waterproof,
        Boolean grip,
        @Size(max = 500) String imageUrl,
        Boolean aiTagged
) {
    public ClothesSpec toSpec() {
        return new ClothesSpec(name, category, color, material, warmth, style,
                Boolean.TRUE.equals(waterproof), Boolean.TRUE.equals(grip), imageUrl,
                Boolean.TRUE.equals(aiTagged));
    }
}
