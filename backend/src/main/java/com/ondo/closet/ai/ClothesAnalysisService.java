package com.ondo.closet.ai;

import com.ondo.closet.ai.dto.AiServerResponses;
import com.ondo.closet.ai.dto.AiServerResponses.Analysis;
import com.ondo.closet.ai.dto.AiServerResponses.DetectedGarment;
import com.ondo.closet.ai.dto.AiServerResponses.OutfitAnalysis;
import com.ondo.closet.ai.dto.AiServerResponses.Suggestion;
import com.ondo.closet.ai.dto.AnalyzeResponse;
import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;
import com.ondo.closet.clothes.WarmLevel;
import com.ondo.closet.image.ImageStorage;
import com.ondo.closet.image.PhotoService;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

/**
 * 사진 → AI 분석 → 배경 지운 옷 사진 저장 → 백엔드 옷 형식(draft)으로 변환.
 * 원본 사진은 저장하지 않는다 (얼굴이 찍혔을 수 있어서).
 */
@Service
public class ClothesAnalysisService {

    private final AiServerClient aiServerClient;
    private final ImageStorage imageStorage;
    private final PhotoService photoService;

    public ClothesAnalysisService(AiServerClient aiServerClient, ImageStorage imageStorage, PhotoService photoService) {
        this.aiServerClient = aiServerClient;
        this.imageStorage = imageStorage;
        this.photoService = photoService;
    }

    public AnalyzeResponse analyze(byte[] image, String filename, String contentType, boolean outfit) {
        long started = System.currentTimeMillis();
        List<AnalyzeResponse.Item> items = new ArrayList<>();
        List<String> skipped;
        List<String> warnings;

        if (outfit) {
            OutfitAnalysis result = aiServerClient.analyzeOutfit(image, filename, contentType);
            List<DetectedGarment> found = result.items() == null ? List.of() : result.items();
            for (int i = 0; i < found.size(); i++) {
                DetectedGarment garment = found.get(i);
                items.add(toItem(i + 1, garment.box(), garment.analysis(), garment.cutoutPngBase64(),
                        garment.detectorLabel()));
            }
            skipped = orEmpty(result.skipped());
            warnings = orEmpty(result.warnings());
        } else {
            Analysis result = aiServerClient.analyze(image, filename, contentType);
            items.add(toItem(1, null, result, result.cutoutPngBase64(), null));
            skipped = List.of();
            warnings = orEmpty(result.warnings());
        }
        return new AnalyzeResponse(outfit ? "outfit" : "single", items, skipped, warnings,
                System.currentTimeMillis() - started);
    }

    private AnalyzeResponse.Item toItem(int index, List<Double> box, Analysis analysis, String cutoutBase64,
                                        String detectorLabel) {
        Suggestion category = orBlank(analysis == null ? null : analysis.category());
        Suggestion subtype = orBlank(analysis == null ? null : analysis.subtype());
        Suggestion warmth = orBlank(analysis == null ? null : analysis.warmth());
        Suggestion style = orBlank(analysis == null ? null : analysis.style());
        List<AiServerResponses.ColorInfo> colors = analysis == null ? List.of() : orEmpty(analysis.colors());

        Category mappedCategory = AiValueMapper.category(category.text());
        Style mappedStyle = AiValueMapper.style(style.text());
        Integer mappedWarmth = AiValueMapper.warmth(warmth.number());
        String color = colors.isEmpty() ? null : toHex(colors.get(0));
        String name = analysis == null ? null : analysis.nameSuggestion();
        String photo = photoService.publicUrl(saveCutout(cutoutBase64));

        AnalyzeResponse.Draft draft = new AnalyzeResponse.Draft(
                name, mappedCategory, color, null,
                mappedWarmth == null ? null : WarmLevel.of(mappedWarmth), mappedWarmth, mappedStyle,
                analysis != null && Boolean.TRUE.equals(analysis.waterproof()),
                analysis != null && Boolean.TRUE.equals(analysis.grip()),
                photo, true);

        List<AnalyzeResponse.TypeCandidate> candidates = category.candidatesOrEmpty().stream()
                .map(c -> new AnalyzeResponse.TypeCandidate(c.label(), AiValueMapper.category(c.label()), c.score()))
                .toList();
        boolean needsReview = mappedCategory == null || mappedStyle == null || mappedWarmth == null
                || color == null || name == null;

        AnalyzeResponse.AiDetail detail = new AnalyzeResponse.AiDetail(
                category.text(), category.confidence(), candidates, subtype.text(),
                style.text(), style.confidence(), warmth.confidence(), colors, detectorLabel, needsReview,
                analysis == null ? List.of() : orEmpty(analysis.warnings()));
        return new AnalyzeResponse.Item(index, box, draft, detail);
    }

    /** AI 대표색 → #RRGGBB (AL-02). hex 가 없으면 색 이름의 대표 견본 */
    private static String toHex(AiServerResponses.ColorInfo info) {
        if (info.hex() != null && ColorPalette.isHex(info.hex())) {
            return info.hex().trim().toLowerCase();
        }
        return ColorPalette.hexOf(info.name());
    }

    /** AI가 준 배경 제거 PNG(base64)를 저장하고 URL을 돌려준다. 없으면 null. */
    private String saveCutout(String base64) {
        if (base64 == null || base64.isBlank()) {
            return null;
        }
        try {
            return imageStorage.saveBytes(Base64.getDecoder().decode(base64), "png");
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private static Suggestion orBlank(Suggestion s) {
        return s == null ? new Suggestion(null, 0.0, List.of()) : s;
    }

    private static <T> List<T> orEmpty(List<T> list) {
        return list == null ? List.of() : list;
    }
}
