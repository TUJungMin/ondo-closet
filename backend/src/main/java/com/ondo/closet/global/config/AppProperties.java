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

    public record Storage(String localDir) {
    }

    public record Closet(int maxItemsPerUser) {
    }

    public record Ai(String serverUrl, int timeoutSeconds) {
        public boolean enabled() {
            return serverUrl != null && !serverUrl.isBlank();
        }
    }
}
