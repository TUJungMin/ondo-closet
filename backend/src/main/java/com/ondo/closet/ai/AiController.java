package com.ondo.closet.ai;

import com.ondo.closet.ai.dto.AnalyzeResponse;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.Map;
import java.util.Set;

/**
 * 옷 사진 AI 분석.
 * - POST /api/clothes/analyze?mode=single  옷 한 벌 사진
 * - POST /api/clothes/analyze?mode=outfit  옷이 여러 벌 찍힌 사진 (상의·하의·신발로 나눔)
 * 응답의 items[].draft 를 확인·수정해서 POST /api/clothes 로 보내면 옷장에 저장된다.
 */
@RestController
public class AiController {

    private static final Set<String> ALLOWED = Set.of(MediaType.IMAGE_JPEG_VALUE, MediaType.IMAGE_PNG_VALUE, "image/webp");

    private final ClothesAnalysisService analysisService;
    private final AiServerClient aiServerClient;

    public AiController(ClothesAnalysisService analysisService, AiServerClient aiServerClient) {
        this.analysisService = analysisService;
        this.aiServerClient = aiServerClient;
    }

    @PostMapping(value = "/api/clothes/analyze", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AnalyzeResponse analyze(@RequestParam("file") MultipartFile file,
                                   @RequestParam(defaultValue = "single") String mode) {
        if (file.isEmpty() || !ALLOWED.contains(file.getContentType())) {
            throw new ApiException(ErrorCode.INVALID_IMAGE);
        }
        if (!mode.equals("single") && !mode.equals("outfit")) {
            throw new ApiException(ErrorCode.INVALID_REQUEST);
        }
        try {
            String filename = file.getOriginalFilename() == null ? "photo" : file.getOriginalFilename();
            return analysisService.analyze(file.getBytes(), filename, file.getContentType(), mode.equals("outfit"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** 화면에서 'AI 연결됨' 표시용. 로그인 없이 호출 가능. */
    @GetMapping("/api/ai/health")
    public Map<String, Object> health() {
        return Map.of("ai", aiServerClient.isHealthy() ? "ok" : "unavailable");
    }
}
