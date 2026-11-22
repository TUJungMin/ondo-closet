package com.ondo.closet;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ondo.closet.ai.AiServerClient;
import com.ondo.closet.ai.dto.AiRecommend;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.atLeast;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** AI 서버는 가짜로 바꾸고, 백엔드 → AI 요청 변환과 응답 가공(자동 고정·선호 스타일)을 확인한다 */
@SpringBootTest(properties = "app.storage.local-dir=build/test-uploads")
@AutoConfigureMockMvc
class OutfitRecommendFlowTest {

    private static final AiRecommend.Context CONTEXT = new AiRecommend.Context(4.2, 4.2, false, false);

    @Autowired
    MockMvc mvc;

    @Autowired
    ObjectMapper objectMapper;

    @MockitoBean
    AiServerClient aiServerClient;

    @Test
    void 고정한_옷과_날씨를_AI_형식으로_보내고_프론트_형식으로_돌려준다() throws Exception {
        String token = guestToken();
        Map<String, Long> ids = closetIds(token);
        long knit = ids.get("크림 니트");
        long slacks = ids.get("브라운 슬랙스");
        long coat = ids.get("카멜 울 코트");

        given(aiServerClient.recommend(any())).willReturn(new AiRecommend.Result(
                List.of(rec(85.0, "체감 5°C라 카멜 울 코트를 걸쳤어요.", item("상의", knit, true), item("하의", slacks, false),
                        item("겉옷", coat, false))),
                CONTEXT, List.of()));

        String body = """
                {"pinnedId":%d,"weather":{"tempC":5,"tempMinC":1,"tempMaxC":9,"sky":"clear","windMs":3},"place":"office"}
                """.formatted(knit);
        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.autoPinned").value(false))
                .andExpect(jsonPath("$.apparentTempC").value(4.2))
                .andExpect(jsonPath("$.recommendations[0].reason").value("체감 5°C라 카멜 울 코트를 걸쳤어요."))
                .andExpect(jsonPath("$.recommendations[0].items[0].id").value(knit))
                .andExpect(jsonPath("$.recommendations[0].items[0].type").value("top"))
                .andExpect(jsonPath("$.recommendations[0].items[0].pinned").value(true))
                .andExpect(jsonPath("$.recommendations[0].items[2].color").value("#c19a6b"))
                .andExpect(jsonPath("$.recommendations[0].items[2].style").value("formal"))
                .andExpect(jsonPath("$.recommendations[0].basis[0].kind").value("날씨"));

        // AI 서버로 나간 요청: 한글 값, HEX → 가장 가까운 색 이름, 옷장 12벌 전체
        ArgumentCaptor<AiRecommend.Request> sent = ArgumentCaptor.forClass(AiRecommend.Request.class);
        verify(aiServerClient).recommend(sent.capture());
        AiRecommend.Request request = sent.getValue();
        assertThat(request.pinnedId()).isEqualTo(knit);
        assertThat(request.place()).isEqualTo("출근");
        assertThat(request.weather().sky()).isEqualTo("맑음");
        assertThat(request.weather().tempMinC()).isEqualTo(1.0);
        assertThat(request.topK()).isEqualTo(3);
        assertThat(request.wardrobe()).hasSize(12);
        AiRecommend.Garment sentKnit = garment(request, "크림 니트");
        assertThat(sentKnit.category()).isEqualTo("상의");
        assertThat(sentKnit.style()).isEqualTo("포멀");
        assertThat(sentKnit.colors()).containsExactly("아이보리");   // #f3ecd9
        assertThat(garment(request, "네이비 바람막이").colors()).containsExactly("남색");
        assertThat(garment(request, "블랙 반팔 티셔츠").style()).isEqualTo("캐주얼");

        // AI 서버로 가는 JSON 은 snake_case
        JsonNode json = objectMapper.valueToTree(request);
        assertThat(json.has("pinned_id")).isTrue();
        assertThat(json.get("weather").has("temp_min_c")).isTrue();
        assertThat(json.get("weather").has("feels_like_c")).isFalse();   // 비어 있으면 안 보냄
    }

    @Test
    void 고정_옷이_없으면_날씨에_맞는_상의를_돌려_가며_고정하고_점수순으로_합친다() throws Exception {
        String token = guestToken();
        Map<String, Long> ids = closetIds(token);
        long knit = ids.get("크림 니트");       // 보온 3
        long sweat = ids.get("그레이 맨투맨");  // 보온 3
        long shirt = ids.get("화이트 옥스퍼드 셔츠");
        long tee = ids.get("블랙 반팔 티셔츠");
        long slacks = ids.get("브라운 슬랙스");
        long denim = ids.get("연청 데님 팬츠");

        // 고정 옷마다 다른 결과. 같은 조합(니트+슬랙스)은 두 번 나와도 한 번만
        given(aiServerClient.recommend(any())).willAnswer(inv -> {
            AiRecommend.Request r = inv.getArgument(0);
            long pin = r.pinnedId();
            if (pin == knit) {
                return new AiRecommend.Result(List.of(rec(70, "니트", item("상의", knit, true), item("하의", slacks, false))),
                        CONTEXT, List.of("니트 경고"));
            }
            if (pin == sweat) {
                return new AiRecommend.Result(List.of(rec(90, "맨투맨", item("상의", sweat, true), item("하의", denim, false))),
                        CONTEXT, List.of());
            }
            return new AiRecommend.Result(List.of(rec(60, "기타", item("상의", pin, true), item("하의", slacks, false)),
                    rec(75, "니트 중복", item("상의", knit, false), item("하의", slacks, true))), CONTEXT, List.of());
        });

        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"weather\":{\"tempC\":12}}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.autoPinned").value(true))
                .andExpect(jsonPath("$.recommendations.length()").value(3))
                .andExpect(jsonPath("$.recommendations[0].reason").value("맨투맨"))
                .andExpect(jsonPath("$.recommendations[0].rank").value(1))
                .andExpect(jsonPath("$.recommendations[1].reason").value("니트 중복"))   // 75 > 70, 같은 조합은 높은 점수만
                .andExpect(jsonPath("$.recommendations[2].score").value(60.0))
                .andExpect(jsonPath("$.warnings.length()").value(0));                  // 1위 조합의 경고만

        // 12°C → 보온 3 에 가까운 상의부터, 상의 4벌 모두 (최대 5벌)
        verify(aiServerClient, atLeast(1)).recommend(argThat(r -> r.pinnedId() == knit));
        verify(aiServerClient, atLeast(1)).recommend(argThat(r -> r.pinnedId() == tee));
        verify(aiServerClient, atLeast(1)).recommend(argThat(r -> r.pinnedId() == shirt));
    }

    @Test
    void 선호_스타일이_맞는_조합을_앞으로_올리고_근거를_붙인다() throws Exception {
        String token = guestToken();
        Map<String, Long> ids = closetIds(token);
        long knit = ids.get("크림 니트");          // formal
        long slacks = ids.get("브라운 슬랙스");    // formal
        long denim = ids.get("연청 데님 팬츠");    // casual
        long sneakers = ids.get("화이트 스니커즈"); // casual

        given(aiServerClient.recommend(any())).willReturn(new AiRecommend.Result(List.of(
                rec(80, "포멀 조합", item("상의", knit, true), item("하의", slacks, false)),
                rec(74, "캐주얼 조합", item("상의", knit, true), item("하의", denim, false), item("신발", sneakers, false))),
                CONTEXT, List.of()));

        String body = """
                {"pinnedId":%d,"weather":{"tempC":15},"preferredStyles":["casual"],"topK":2}
                """.formatted(knit);
        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                // 74 + 10×2/3 ≈ 80.7 > 80
                .andExpect(jsonPath("$.recommendations[0].reason").value("캐주얼 조합"))
                .andExpect(jsonPath("$.recommendations[0].score").value(74.0))
                .andExpect(jsonPath("$.recommendations[0].basis[1].kind").value("취향"))
                .andExpect(jsonPath("$.recommendations[1].reason").value("포멀 조합"));

        // 선호 스타일이 있으면 후보를 넉넉히(6개) 받는다
        verify(aiServerClient).recommend(argThat(r -> r.topK() == 6));
    }

    @Test
    void 남의_옷이나_없는_옷을_고정하면_404() throws Exception {
        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + guestToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"pinnedId\":999999,\"weather\":{\"tempC\":10}}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("CLOTHES_NOT_FOUND"));
    }

    @Test
    void 기온이_없거나_없는_장소면_400() throws Exception {
        String token = guestToken();
        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"weather\":{}}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"weather\":{\"tempC\":10},\"place\":\"cafe\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void 옷장이_비었으면_400_AI가_꺼져_있으면_503() throws Exception {
        String token = guestToken();
        Map<String, Long> ids = closetIds(token);
        given(aiServerClient.recommend(any())).willThrow(new ApiException(ErrorCode.AI_UNAVAILABLE));

        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"weather\":{\"tempC\":10}}"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("AI_UNAVAILABLE"));

        for (long id : ids.values()) {
            mvc.perform(delete("/api/clothes/" + id).header("Authorization", "Bearer " + token));
        }
        mvc.perform(post("/api/outfits/recommend").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"weather\":{\"tempC\":10}}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("EMPTY_CLOSET"));
    }

    private static AiRecommend.Recommendation rec(double score, String reason, AiRecommend.Item... items) {
        return new AiRecommend.Recommendation(1, List.of(items), score, reason,
                List.of(new AiRecommend.Basis("날씨", "기온 5°C, 맑음")), Map.of("보온", 0.9));
    }

    private static AiRecommend.Item item(String slot, long id, boolean pinned) {
        return new AiRecommend.Item(slot, id, "옷", "상의", pinned);
    }

    private static AiRecommend.Garment garment(AiRecommend.Request request, String name) {
        return request.wardrobe().stream().filter(g -> g.name().equals(name)).findFirst().orElseThrow();
    }

    private Map<String, Long> closetIds(String token) throws Exception {
        MvcResult result = mvc.perform(get("/api/clothes").header("Authorization", "Bearer " + token)).andReturn();
        JsonNode list = objectMapper.readTree(result.getResponse().getContentAsString());
        Map<String, Long> ids = new HashMap<>();
        list.forEach(c -> ids.put(c.get("name").asText(), c.get("id").asLong()));
        return ids;
    }

    private String guestToken() throws Exception {
        MvcResult result = mvc.perform(post("/api/auth/guest")).andExpect(status().isCreated()).andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("accessToken").asText();
    }
}
