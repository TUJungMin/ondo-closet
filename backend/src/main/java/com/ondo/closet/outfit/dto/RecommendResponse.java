package com.ondo.closet.outfit.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;

import java.util.List;
import java.util.Map;

/** POST /api/outfits/recommend 응답. AI 결과에 옷 사진(photo)과 프론트 값을 붙여서 돌려준다. */
public record RecommendResponse(
        List<Recommendation> recommendations,
        double apparentTempC,        // 날씨 기준 체감 온도
        double effectiveTempC,       // 추천에 실제로 쓴 온도 (착용 기록 보정 포함)
        boolean autoPinned,          // 고정 옷 없이 요청해서 서버가 고정 옷을 골랐는지
        List<String> warnings
) {

    public record Recommendation(
            int rank,
            double score,            // AI 점수 0~100 (순서는 선호 스타일 보너스까지 반영)
            String reason,           // 왜 이 조합인지 한 줄
            List<Basis> basis,       // 근거 목록 (날씨, 고정 옷, 장소, 취향 ...)
            Map<String, Double> breakdown,
            List<Item> items         // 상의 → 하의 → 겉옷 → 신발 순
    ) {
    }

    public record Item(String slot, Long id, String name, Category type, String color, Style style,
                       String photo, boolean pinned) {
    }

    public record Basis(String kind, String text) {
    }
}
