package com.ondo.closet.clothes.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;
import com.ondo.closet.clothes.WarmLevel;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * 옷 부분 수정(PATCH) 요청 (AL-07). 보낸 필드만 바뀌고 빠진 필드(null)는 그대로 남는다.
 * 사진을 지우려면 photo 에 빈 문자열("")을 보낸다.
 * 예: {"water": true} / {"photo": "data:image/jpeg;base64,..."}
 */
public record ClothesPatchRequest(
        @Size(max = 60, message = "이름은 60자 이하입니다.")
        @Pattern(regexp = "(?s).*\\S.*", message = "이름을 입력해 주세요.") String name,
        Category type,
        @Pattern(regexp = "^#[0-9a-fA-F]{6}$", message = "색상은 #RRGGBB 형식으로 보내 주세요.") String color,
        @Size(max = 30) String material,
        WarmLevel warm,
        @Min(1) @Max(5) Integer warmScore,
        Style style,
        Boolean water,
        Boolean grip,
        @Size(max = 4_500_000, message = "사진 데이터가 너무 큽니다.") String photo,
        Boolean aiTagged
) {
}
