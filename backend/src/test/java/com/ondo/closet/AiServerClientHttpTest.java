package com.ondo.closet;

import com.ondo.closet.ai.AiServerClient;
import com.ondo.closet.ai.dto.AiRecommend;
import com.ondo.closet.ai.dto.AiServerResponses.Analysis;
import com.ondo.closet.global.config.AppProperties;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** 진짜 HTTP 로 가짜 AI 서버를 불러서, 사진이 multipart 'file' 로 제대로 나가는지 확인한다 */
class AiServerClientHttpTest {

    private HttpServer server;
    private final AtomicReference<String> received = new AtomicReference<>();

    @BeforeEach
    void startFakeAiServer() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/ai/analyze", exchange -> {
            String contentType = exchange.getRequestHeaders().getFirst("Content-Type");
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.ISO_8859_1);
            received.set(contentType + "\n" + body);
            byte[] json = """
                    {"category":{"value":"상의","confidence":0.9},"name_suggestion":"남색 니트","colors":[]}
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, json.length);
            exchange.getResponseBody().write(json);
            exchange.close();
        });
        server.createContext("/ai/recommend", exchange -> {
            received.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] json = """
                    {"recommendations":[{"rank":1,"items":[{"slot":"상의","garment_id":7,"name":"니트","category":"상의","pinned":true}],
                      "score":80.0,"reason":"좋아요","basis":[],"breakdown":{}}],
                     "excluded":[],"context":{"apparent_temp_c":9.5,"personal_offset_c":0,"effective_temp_c":9.5,"wet":false,"snowy":false},
                     "warnings":[]}
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, json.length);
            exchange.getResponseBody().write(json);
            exchange.close();
        });
        server.start();
    }

    @AfterEach
    void stop() {
        server.stop(0);
    }

    @Test
    void 사진을_multipart_file_로_보내고_응답을_읽는다() {
        AiServerClient client = client("http://127.0.0.1:" + server.getAddress().getPort());

        Analysis result = client.analyze(new byte[]{1, 2, 3}, "knit.jpg", "image/jpeg");

        assertThat(result.category().text()).isEqualTo("상의");
        assertThat(result.nameSuggestion()).isEqualTo("남색 니트");
        assertThat(received.get())
                .startsWith("multipart/form-data")
                .contains("name=\"file\"")
                .contains("filename=\"knit.jpg\"")
                .contains("Content-Type: image/jpeg");
    }

    @Test
    void 추천_요청을_snake_case_JSON으로_보내고_응답을_읽는다() {
        AiServerClient client = client("http://127.0.0.1:" + server.getAddress().getPort());
        AiRecommend.Request request = new AiRecommend.Request(
                List.of(new AiRecommend.Garment(7L, "니트", "상의", List.of("남색"), 4, "캐주얼", false, false)),
                7L, new AiRecommend.Weather(10, null, 4.0, null, "맑음", null, 2.0), "일상", 3);

        AiRecommend.Result result = client.recommend(request);

        assertThat(result.recommendations().get(0).items().get(0).garmentId()).isEqualTo(7L);
        assertThat(result.context().apparentTempC()).isEqualTo(9.5);
        assertThat(received.get())
                .contains("\"pinned_id\":7", "\"temp_c\":10", "\"temp_min_c\":4", "\"top_k\":3", "\"category\":\"상의\"")
                .doesNotContain("feels_like_c");
    }

    @Test
    void AI_서버가_꺼져_있으면_AI_UNAVAILABLE() {
        server.stop(0);
        AiServerClient client = client("http://127.0.0.1:" + server.getAddress().getPort());

        assertThatThrownBy(() -> client.analyze(new byte[]{1}, "a.jpg", "image/jpeg"))
                .isInstanceOf(ApiException.class)
                .satisfies(e -> assertThat(((ApiException) e).errorCode()).isEqualTo(ErrorCode.AI_UNAVAILABLE));
        assertThat(client.isHealthy()).isFalse();
    }

    private AiServerClient client(String url) {
        AppProperties props = new AppProperties(null, null, null, null, new AppProperties.Ai(url, 10));
        return new AiServerClient(RestClient.builder(), props);
    }
}
