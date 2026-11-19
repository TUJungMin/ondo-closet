package com.ondo.closet.ai.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * 준호 님 AI 서버 POST /ai/recommend 요청·응답 (ai/ondo_ai/schemas.py 의 RecommendRequest / RecommendResult).
 * 필드 이름은 snake_case, 값은 한글 그대로.
 */
public final class AiRecommend {

    private AiRecommend() {
    }

    // ---------------------------------------------------------------- 요청

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Request(
            List<Garment> wardrobe,
            @JsonProperty("pinned_id") Long pinnedId,
            Weather weather,
            String place,
            @JsonProperty("top_k") int topK
    ) {
    }

    /** status·favorite 는 아직 백엔드에 없어서 보내지 않는다 (AI 기본값: 입을 수 있음) */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Garment(
            Long id,
            String name,
            String category,
            List<String> colors,
            Integer warmth,
            String style,
            boolean waterproof,
            boolean grip
    ) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Weather(
            @JsonProperty("temp_c") double tempC,
            @JsonProperty("feels_like_c") Double feelsLikeC,
            @JsonProperty("temp_min_c") Double tempMinC,
            @JsonProperty("temp_max_c") Double tempMaxC,
            String sky,
            @JsonProperty("precip_prob") Double precipProb,
            @JsonProperty("wind_ms") Double windMs
    ) {
    }

    // ---------------------------------------------------------------- 응답

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Result(List<Recommendation> recommendations, Context context, List<String> warnings) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Recommendation(int rank, List<Item> items, double score, String reason, List<Basis> basis,
                                 Map<String, Double> breakdown) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Item(String slot, @JsonProperty("garment_id") Long garmentId, String name, String category,
                       boolean pinned) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Basis(String kind, String text) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Context(
            @JsonProperty("apparent_temp_c") double apparentTempC,
            @JsonProperty("effective_temp_c") double effectiveTempC,
            boolean wet,
            boolean snowy
    ) {
    }
}
