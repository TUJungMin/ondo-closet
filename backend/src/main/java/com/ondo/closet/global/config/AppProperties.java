package com.ondo.closet.global.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.Arrays;
import java.util.List;

/** application.yml 의 app.* 설정을 한곳에 모은 클래스 */
@ConfigurationProperties(prefix = "app")
public record AppProperties(Jwt jwt, Cors cors, Storage storage, Closet closet, Ai ai) {

    public record Jwt(String secret, long expirationHours) {
    }

    public record Cors(String allowedOrigins) {
        public List<String> originList() {
            return Arrays.stream(allowedOrigins.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .toList();
        }
    }

    /**
     * @param localDir      사진 파일을 저장할 폴더
     * @param publicBaseUrl 응답의 photo 앞에 붙일 서버 주소 (예: http://localhost:8080). 프론트가 다른 포트에서 떠도 사진이 보이게 한다
     */
    public record Storage(String localDir, String publicBaseUrl) {
    }

    public record Closet(int maxItemsPerUser) {
    }

    public record Ai(String serverUrl, int timeoutSeconds) {
        public boolean enabled() {
            return serverUrl != null && !serverUrl.isBlank();
        }
    }
}
