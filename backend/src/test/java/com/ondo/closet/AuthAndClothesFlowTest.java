package com.ondo.closet;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "app.storage.local-dir=build/test-uploads")
@AutoConfigureMockMvc
class AuthAndClothesFlowTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    ObjectMapper objectMapper;

    private static final String COAT = """
            {"name":"카멜 울 코트","category":"OUTER","color":"카멜","material":"울",
             "warmth":4,"style":"FORMAL","waterproof":false,"grip":false}
            """;

    @Test
    void 회원가입_로그인_내정보() throws Exception {
        String token = signup("tester01");

        mvc.perform(get("/api/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.loginId").value("tester01"))
                .andExpect(jsonPath("$.guest").value(false));

        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"tester01\",\"password\":\"password123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").isNotEmpty());
    }

    @Test
    void 중복_아이디와_틀린_비밀번호() throws Exception {
        signup("tester02");

        mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"tester02\",\"password\":\"password123\",\"nickname\":\"중복\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("DUPLICATE_LOGIN_ID"));

        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"tester02\",\"password\":\"wrong-password\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void 토큰_없으면_401() throws Exception {
        mvc.perform(get("/api/clothes"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));

        mvc.perform(get("/api/clothes").header("Authorization", "Bearer not-a-token"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 게스트는_샘플_옷장으로_시작() throws Exception {
        MvcResult result = mvc.perform(post("/api/auth/guest"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.user.guest").value(true))
                .andReturn();
        String token = readToken(result);

        mvc.perform(get("/api/clothes").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(12));
    }

    @Test
    void 옷장_등록_수정_삭제와_남의_옷_접근_차단() throws Exception {
        String owner = signup("owner01");
        String other = signup("other01");

        MvcResult created = mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + owner)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.category").value("OUTER"))
                .andReturn();
        long id = objectMapper.readTree(created.getResponse().getContentAsString()).get("id").asLong();

        mvc.perform(put("/api/clothes/" + id).header("Authorization", "Bearer " + owner)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT.replace("\"warmth\":4", "\"warmth\":5")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.warmth").value(5));

        // 다른 사용자는 id를 알아도 조회·삭제할 수 없음
        mvc.perform(get("/api/clothes/" + id).header("Authorization", "Bearer " + other))
                .andExpect(status().isNotFound());
        mvc.perform(delete("/api/clothes/" + id).header("Authorization", "Bearer " + other))
                .andExpect(status().isNotFound());

        mvc.perform(delete("/api/clothes/" + id).header("Authorization", "Bearer " + owner))
                .andExpect(status().isNoContent());
        mvc.perform(get("/api/clothes/" + id).header("Authorization", "Bearer " + owner))
                .andExpect(status().isNotFound());
    }

    @Test
    void 잘못된_입력은_필드별_에러() throws Exception {
        String token = signup("validator");
        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(COAT.replace("\"warmth\":4", "\"warmth\":9")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors.warmth").exists());

        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(COAT.replace("OUTER", "HAT")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void 이미지_업로드() throws Exception {
        String token = signup("uploader");
        var jpg = new MockMultipartFile("file", "coat.jpg", "image/jpeg", new byte[]{1, 2, 3});
        mvc.perform(multipart("/api/clothes/image").file(jpg).header("Authorization", "Bearer " + token))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.imageUrl").value(org.hamcrest.Matchers.startsWith("/uploads/")));

        var txt = new MockMultipartFile("file", "a.txt", "text/plain", new byte[]{1});
        mvc.perform(multipart("/api/clothes/image").file(txt).header("Authorization", "Bearer " + token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_IMAGE"));
    }

    private String signup(String loginId) throws Exception {
        MvcResult result = mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"" + loginId + "\",\"password\":\"password123\",\"nickname\":\"테스터\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        return readToken(result);
    }

    private String readToken(MvcResult result) throws Exception {
        JsonNode body = objectMapper.readTree(result.getResponse().getContentAsString());
        return body.get("accessToken").asText();
    }
}
