package com.ondo.closet.ai.dto;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;

import java.util.List;

/**
 * POST /api/clothes/analyze 응답.
 * 한 벌 사진이든 여러 벌 사진이든 items 목록으로 돌려준다 (한 벌이면 items 1개, box 는 null).
 * 각 item 의 draft 를 사용자가 확인·수정한 뒤 그대로 POST /api/clothes 에 보내면 저장된다.
 */
public record AnalyzeResponse(
        String mode,                 // single | outfit
        List<Item> items,
        List<String> skipped,        // 찾았지만 옷장 종류가 아니라 뺀 것 (가방, 모자 등)
        List<String> warnings,       // 사용자에게 그대로 보여줄 안내 문장
        long elapsedMs
) {

    public record Item(
            int index,               // 사진 위에서 아래 순서 (1부터)
            List<Double> box,        // 사진 안 위치 [왼쪽, 위, 오른쪽, 아래], 0~1. 한 벌 사진이면 null
            Draft draft,
            AiDetail ai
    ) {
    }

    /** POST /api/clothes 요청과 같은 모양. AI가 확신하지 못한 값은 null 이므로 화면에서 채워야 한다. */
    public record Draft(
            String name,
            Category category,
            String color,
            String material,
            Integer warmth,
            Style style,
            boolean waterproof,
            boolean grip,
            String imageUrl,         // 배경을 지운 옷 사진 (서버에 저장됨)
            boolean aiTagged
    ) {
    }

    /** 화면에 'AI 제안'과 확신도를 보여주기 위한 원래 값 */
    public record AiDetail(
            String category,         // AI 원래 값 (상의, 바지 ...), 확신 낮으면 null
            double categoryConfidence,
            List<CategoryCandidate> categoryCandidates,
            String subtype,          // 세부 종류 (니트, 청바지 ...)
            String style,            // AI 원래 값 (캐주얼, 스트릿 ...)
            double styleConfidence,
            double warmthConfidence,
            List<AiServerResponses.ColorInfo> colors,
            String detectorLabel,    // 여러 벌 사진에서 검출 모델이 붙인 이름 (jacket, pants ...)
            boolean needsReview,     // 종류·스타일·보온성 중 비어 있는 값이 있으면 true
            List<String> warnings
    ) {
    }

    public record CategoryCandidate(String label, Category category, double score) {
    }
}
