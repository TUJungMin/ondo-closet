package com.ondo.closet.outfit.dto;

import com.ondo.closet.clothes.Style;
import com.ondo.closet.outfit.Place;
import com.ondo.closet.outfit.Sky;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * POST /api/outfits/recommend 요청.
 * 예: {"pinnedId":7,"weather":{"tempC":8,"feelsLikeC":5,"tempMinC":3,"tempMaxC":12,"sky":"clear","precipProb":0.1,"windMs":3},
 *      "place":"office","preferredStyles":["casual"]}
 */
public record RecommendRequest(
        Long pinnedId,                      // 선택 (AL-11). 없으면 서버가 상의 후보를 돌려 가며 고정해 본다
        @NotNull(message = "날씨를 입력해 주세요.") @Valid WeatherInput weather,
        Place place,                        // 없으면 daily
        @Min(1) @Max(5) Integer topK,       // 없으면 3
        @Size(max = 5) List<Style> preferredStyles   // 선택 (AL-13). 맞는 스타일 조합을 앞으로
) {

    /** 날씨 (AL-10). 추위 민감도는 프론트가 feelsLikeC 에 더해서 보낸다 (AL-12) */
    public record WeatherInput(
            @NotNull(message = "기온을 입력해 주세요.") @DecimalMin("-40") @DecimalMax("50") Double tempC,
            @DecimalMin("-50") @DecimalMax("60") Double feelsLikeC,   // 없으면 AI가 바람으로 추정
            @DecimalMin("-50") @DecimalMax("60") Double tempMinC,
            @DecimalMin("-50") @DecimalMax("60") Double tempMaxC,
            Sky sky,                                                  // 없으면 clear
            @DecimalMin("0") @DecimalMax("1") Double precipProb,     // 강수 확률 0~1
            @DecimalMin("0") @DecimalMax("60") Double windMs
    ) {
    }
}
