package com.ondo.closet.ai.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

/**
 * 준호 님 AI 서버(ai/ondo_ai/service.py)가 돌려주는 JSON 형식.
 * 필드 이름은 AI 서버 그대로(snake_case)이고, 값은 한글이다 (상의, 캐주얼 등).
 * 모르는 필드가 추가돼도 깨지지 않게 ignoreUnknown 을 켠다.
 */
public final class AiServerResponses {

    private AiServerResponses() {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Candidate(String label, double score) {
    }

    /** AI 제안 한 항목. 확신이 낮으면 value 가 null 이고 candidates 만 온다. value 는 문자열 또는 숫자. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Suggestion(JsonNode value, double confidence, List<Candidate> candidates) {

        public String text() {
            return value == null || value.isNull() ? null : value.asText();
        }

        public Integer number() {
            return value == null || !value.canConvertToInt() ? null : value.asInt();
        }

        public List<Candidate> candidatesOrEmpty() {
            return candidates == null ? List.of() : candidates;
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record ColorInfo(String name, String hex, double ratio) {
    }

    /** POST /ai/analyze 응답 (옷 한 벌) */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Analysis(
            Suggestion category,
            Suggestion subtype,
            @JsonProperty("name_suggestion") String nameSuggestion,
            List<ColorInfo> colors,
            Suggestion warmth,
            Suggestion style,
            Boolean waterproof,
            Boolean grip,
            List<String> warnings,
            @JsonProperty("cutout_png_base64") String cutoutPngBase64
    ) {
    }

    /** 여러 옷 사진에서 찾은 옷 한 벌 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record DetectedGarment(
            List<Double> box,
            @JsonProperty("detector_label") String detectorLabel,
            @JsonProperty("detector_score") double detectorScore,
            Analysis analysis,
            @JsonProperty("cutout_png_base64") String cutoutPngBase64
    ) {
    }

    /** POST /ai/analyze-outfit 응답 (옷 여러 벌) */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record OutfitAnalysis(List<DetectedGarment> items, List<String> skipped, List<String> warnings) {
    }
}
