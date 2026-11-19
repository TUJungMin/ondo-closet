package com.ondo.closet.ai;

import com.ondo.closet.ai.dto.AiServerResponses.Analysis;
import com.ondo.closet.ai.dto.AiServerResponses.OutfitAnalysis;
import com.ondo.closet.global.config.AppProperties;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Map;

/**
 * 준호 님 AI 추론 서버를 HTTP로 호출한다.
 * 서버 주소는 AI_SERVER_URL 환경변수 (기본 http://127.0.0.1:8000).
 * 원본 사진은 이 서버와 AI 서버 어디에도 저장하지 않는다. 배경을 지운 옷 사진만 백엔드가 저장한다.
 */
@Component
public class AiServerClient {

    private static final Logger log = LoggerFactory.getLogger(AiServerClient.class);

    private final RestClient restClient;
    private final boolean enabled;

    public AiServerClient(RestClient.Builder builder, AppProperties props) {
        this.enabled = props.ai().enabled();
        HttpClient httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)   // uvicorn 은 HTTP/1.1 서버
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(Duration.ofSeconds(props.ai().timeoutSeconds()));
        this.restClient = builder
                .baseUrl(enabled ? props.ai().serverUrl() : "http://ai-disabled.invalid")
                .requestFactory(factory)
                .build();
    }

    /** 옷 한 벌이 찍힌 사진 */
    public Analysis analyze(byte[] image, String filename, String contentType) {
        return post("/ai/analyze", image, filename, contentType, Analysis.class);
    }

    /** 옷이 여러 벌 찍힌 사진 (착용 사진 등) */
    public OutfitAnalysis analyzeOutfit(byte[] image, String filename, String contentType) {
        return post("/ai/analyze-outfit", image, filename, contentType, OutfitAnalysis.class);
    }

    /** AI 서버가 살아 있는지 (모델을 올리지는 않는다) */
    public boolean isHealthy() {
        if (!enabled) {
            return false;
        }
        try {
            Map<?, ?> body = restClient.get().uri("/ai/health").retrieve().body(Map.class);
            return body != null && "ok".equals(body.get("status"));
        } catch (RestClientException e) {
            return false;
        }
    }

    private <T> T post(String path, byte[] image, String filename, String contentType, Class<T> type) {
        if (!enabled) {
            throw new ApiException(ErrorCode.AI_UNAVAILABLE);
        }
        MultipartBodyBuilder parts = new MultipartBodyBuilder();
        parts.part("file", new ByteArrayResource(image) {
            @Override
            public String getFilename() {
                return filename;
            }
        }).contentType(MediaType.parseMediaType(contentType));
        try {
            T body = restClient.post()
                    .uri(path)
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(parts.build())
                    .retrieve()
                    .body(type);
            if (body == null) {
                throw new ApiException(ErrorCode.AI_UNAVAILABLE);
            }
            return body;
        } catch (HttpClientErrorException e) {
            // AI 서버가 사진을 거절한 경우: 413 = 너무 큼, 400 = 열 수 없는 파일
            log.warn("AI server rejected image: {} {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new ApiException(e.getStatusCode().value() == 413 ? ErrorCode.IMAGE_TOO_LARGE : ErrorCode.INVALID_IMAGE);
        } catch (RestClientException e) {
            // 연결 실패, 시간 초과, 5xx
            log.warn("AI server call failed: {}", e.getMessage());
            throw new ApiException(ErrorCode.AI_UNAVAILABLE);
        }
    }
}
