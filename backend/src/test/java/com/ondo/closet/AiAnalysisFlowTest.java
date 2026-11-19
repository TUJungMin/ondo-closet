package com.ondo.closet;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ondo.closet.ai.AiServerClient;
import com.ondo.closet.ai.dto.AiServerResponses.Analysis;
import com.ondo.closet.ai.dto.AiServerResponses.OutfitAnalysis;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.hamcrest.Matchers.startsWith;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** AI 서버는 가짜(mock)로 바꾸고, 백엔드의 변환·사진 저장·응답 형식을 확인한다 */
@SpringBootTest(properties = "app.storage.local-dir=build/test-uploads")
@AutoConfigureMockMvc
class AiAnalysisFlowTest {

    /** 1x1 투명 PNG */
    private static final String PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

    /** 준호 님 AI 서버의 /ai/analyze-outfit 응답 예시 (README 기준, 일부 줄임) */
    private static final String OUTFIT_JSON = """
            {"source":"ai","items":[
              {"box":[0.33,0.0,0.9,0.48],"detector_label":"jacket","detector_score":0.73,
               "analysis":{"category":{"value":"상의","confidence":0.96,"candidates":[{"label":"상의","score":0.96}]},
                           "subtype":{"value":"후드티","confidence":0.7},"name_suggestion":"갈색 후드티",
                           "colors":[{"name":"갈색","hex":"#423529","ratio":0.93}],
                           "warmth":{"value":4,"confidence":0.8},"style":{"value":"스트릿","confidence":0.7},
                           "waterproof":false,"grip":false,"warnings":[]},
               "cutout_png_base64":"%s"},
              {"box":[0.34,0.43,0.77,0.97],"detector_label":"pants","detector_score":0.97,
               "analysis":{"category":{"value":"바지","confidence":0.99},"name_suggestion":"검정 코듀로이 팬츠",
                           "colors":[{"name":"검정","hex":"#2b2b23","ratio":0.96}],
                           "warmth":{"value":3,"confidence":0.7},"style":{"value":"캐주얼","confidence":0.65}},
               "cutout_png_base64":"%s"},
              {"box":[0.34,0.91,0.71,0.98],"detector_label":"shoe","detector_score":0.97,
               "analysis":{"category":{"value":null,"confidence":0.41,"candidates":[{"label":"신발","score":0.41},{"label":"상의","score":0.2}]},
                           "colors":[],"warmth":{"value":null},"style":{"value":null},
                           "warnings":["옷을 또렷하게 가려내지 못했어요."]},
               "cutout_png_base64":null}],
             "skipped":["가방"],"warnings":[]}
            """.formatted(PNG, PNG);

    @Autowired
    MockMvc mvc;

    @Autowired
    ObjectMapper objectMapper;

    @MockitoBean
    AiServerClient aiServerClient;

    @Test
    void 착용_사진을_옷별로_나눠_백엔드_형식으로_돌려준다() throws Exception {
        given(aiServerClient.analyzeOutfit(any(), anyString(), anyString()))
                .willReturn(objectMapper.readValue(OUTFIT_JSON, OutfitAnalysis.class));
        String token = guestToken();

        MvcResult result = mvc.perform(multipart("/api/clothes/analyze").file(jpg()).param("mode", "outfit")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mode").value("outfit"))
                .andExpect(jsonPath("$.items.length()").value(3))
                .andExpect(jsonPath("$.skipped[0]").value("가방"))
                // 상의: 종류·보온성·색은 채워지고, 백엔드에 없는 스타일(스트릿)은 비워서 확인 필요
                .andExpect(jsonPath("$.items[0].draft.category").value("TOP"))
                .andExpect(jsonPath("$.items[0].draft.name").value("갈색 후드티"))
                .andExpect(jsonPath("$.items[0].draft.color").value("갈색"))
                .andExpect(jsonPath("$.items[0].draft.warmth").value(4))
                .andExpect(jsonPath("$.items[0].draft.style").doesNotExist())
                .andExpect(jsonPath("$.items[0].draft.imageUrl").value(startsWith("/uploads/")))
                .andExpect(jsonPath("$.items[0].ai.style").value("스트릿"))
                .andExpect(jsonPath("$.items[0].ai.needsReview").value(true))
                // 바지: 모두 채워짐
                .andExpect(jsonPath("$.items[1].draft.category").value("PANTS"))
                .andExpect(jsonPath("$.items[1].draft.style").value("CASUAL"))
                .andExpect(jsonPath("$.items[1].ai.needsReview").value(false))
                // 신발: 확신이 낮아 종류가 비고, 후보는 백엔드 값으로도 알려줌
                .andExpect(jsonPath("$.items[2].draft.category").doesNotExist())
                .andExpect(jsonPath("$.items[2].ai.categoryCandidates[0].category").value("SHOES"))
                .andExpect(jsonPath("$.items[2].ai.warnings[0]").exists())
                .andReturn();

        // 확인·수정한 draft 를 그대로 옷장에 저장할 수 있어야 한다
        JsonNode draft = objectMapper.readTree(result.getResponse().getContentAsString()).at("/items/1/draft");
        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(draft.toString()))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.aiTagged").value(true))
                .andExpect(jsonPath("$.imageUrl").value(startsWith("/uploads/")));
    }

    @Test
    void 옷_한_벌_사진() throws Exception {
        String json = """
                {"category":{"value":"겉옷","confidence":0.99},"name_suggestion":"베이지 트렌치코트",
                 "colors":[{"name":"베이지","hex":"#ad9b7a","ratio":0.95}],
                 "warmth":{"value":3,"confidence":0.6},"style":{"value":"포멀","confidence":0.48},
                 "cutout_png_base64":"%s"}
                """.formatted(PNG);
        given(aiServerClient.analyze(any(), anyString(), anyString()))
                .willReturn(objectMapper.readValue(json, Analysis.class));

        mvc.perform(multipart("/api/clothes/analyze").file(jpg()).header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mode").value("single"))
                .andExpect(jsonPath("$.items[0].box").doesNotExist())
                .andExpect(jsonPath("$.items[0].draft.category").value("OUTER"))
                .andExpect(jsonPath("$.items[0].draft.style").value("FORMAL"));
    }

    @Test
    void AI_서버가_꺼져_있으면_503() throws Exception {
        given(aiServerClient.analyzeOutfit(any(), anyString(), anyString()))
                .willThrow(new ApiException(ErrorCode.AI_UNAVAILABLE));

        mvc.perform(multipart("/api/clothes/analyze").file(jpg()).param("mode", "outfit")
                        .header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("AI_UNAVAILABLE"));
    }

    @Test
    void 이미지가_아니거나_로그인_안_하면_거절() throws Exception {
        var txt = new MockMultipartFile("file", "a.txt", "text/plain", new byte[]{1});
        mvc.perform(multipart("/api/clothes/analyze").file(txt).header("Authorization", "Bearer " + guestToken()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_IMAGE"));

        mvc.perform(multipart("/api/clothes/analyze").file(jpg()))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void AI_상태는_로그인_없이_확인() throws Exception {
        given(aiServerClient.isHealthy()).willReturn(true);
        mvc.perform(get("/api/ai/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ai").value("ok"));
    }

    private MockMultipartFile jpg() {
        return new MockMultipartFile("file", "outfit.jpg", "image/jpeg", new byte[]{1, 2, 3});
    }

    private String guestToken() throws Exception {
        MvcResult result = mvc.perform(post("/api/auth/guest")).andExpect(status().isCreated()).andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("accessToken").asText();
    }
}
