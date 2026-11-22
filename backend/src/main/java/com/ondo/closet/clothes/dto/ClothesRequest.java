package com.ondo.closet.clothes.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;
import com.ondo.closet.clothes.WarmLevel;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * 옷 등록(POST)·전체 수정(PUT) 요청. 이름·값은 프론트 기준 (AL-01~08).
 * 예: {"name":"카멜 울 코트","type":"outer","color":"#c19a6b","warm":"warm","style":"formal",
 *      "water":false,"grip":false,"photo":"data:image/jpeg;base64,..."}
 */
public record ClothesRequest(
        @NotBlank(message = "이름을 입력해 주세요.") @Size(max = 60, message = "이름은 60자 이하입니다.") String name,
        @NotNull(message = "종류를 선택해 주세요.") Category type,
        @NotBlank(message = "색상을 선택해 주세요.")
        @Pattern(regexp = "^#[0-9a-fA-F]{6}$", message = "색상은 #RRGGBB 형식으로 보내 주세요.") String color,
        @Size(max = 30) String material,
        @NotNull(message = "보온성을 선택해 주세요.") WarmLevel warm,
        @Min(1) @Max(5) Integer warmScore,   // 선택. AI 분석이 준 1~5 세부값 (draft 에 들어 있음)
        @NotNull(message = "스타일을 선택해 주세요.") Style style,
        Boolean water,
        Boolean grip,
        @Size(max = 4_500_000, message = "사진 데이터가 너무 큽니다.") String photo,  // dataURL 또는 서버 사진 주소
        Boolean aiTagged
) {
}
