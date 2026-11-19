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
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
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

    /** 프론트 형식 (AL-01~08): 소문자 값, type/warm/water 이름, HEX 색 */
    private static final String COAT = """
            {"name":"카멜 울 코트","type":"outer","color":"#C19A6B","material":"울",
             "warm":"warm","style":"formal","water":false,"grip":false}
            """;

    /** 1x1 PNG dataURL (프론트가 canvas.toDataURL 로 만드는 형식) */
    private static final String PNG_DATA_URL = "data:image/png;base64,"
            + "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

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
                .andExpect(jsonPath("$.length()").value(12))
                .andExpect(jsonPath("$[0].type").exists())
                .andExpect(jsonPath("$[0].color").value(startsWith("#")));

        mvc.perform(get("/api/clothes").param("type", "outer").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].type").value("outer"));
    }

    @Test
    void 옷장_등록_수정_삭제와_남의_옷_접근_차단() throws Exception {
        String owner = signup("owner01");
        String other = signup("other01");

        MvcResult created = mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + owner)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.type").value("outer"))
                .andExpect(jsonPath("$.color").value("#c19a6b"))
                .andExpect(jsonPath("$.warm").value("warm"))
                .andExpect(jsonPath("$.warmScore").value(4))
                .andExpect(jsonPath("$.style").value("formal"))
                .andExpect(jsonPath("$.water").value(false))
                .andExpect(jsonPath("$.photo").doesNotExist())
                .andReturn();
        long id = objectMapper.readTree(created.getResponse().getContentAsString()).get("id").asLong();

        mvc.perform(put("/api/clothes/" + id).header("Authorization", "Bearer " + owner)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT.replace("\"warm\":\"warm\"", "\"warm\":\"light\"")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.warm").value("light"))
                .andExpect(jsonPath("$.warmScore").value(2));

        // 다른 사용자는 id를 알아도 조회·수정·삭제할 수 없음
        mvc.perform(get("/api/clothes/" + id).header("Authorization", "Bearer " + other))
                .andExpect(status().isNotFound());
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + other)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"water\":true}"))
                .andExpect(status().isNotFound());
        mvc.perform(delete("/api/clothes/" + id).header("Authorization", "Bearer " + other))
                .andExpect(status().isNotFound());

        mvc.perform(delete("/api/clothes/" + id).header("Authorization", "Bearer " + owner))
                .andExpect(status().isNoContent());
        mvc.perform(get("/api/clothes/" + id).header("Authorization", "Bearer " + owner))
                .andExpect(status().isNotFound());
    }

    @Test
    void PATCH는_보낸_값만_바꾼다() throws Exception {
        String token = signup("patcher");
        long id = createCoat(token);

        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"water\":true}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.water").value(true))
                .andExpect(jsonPath("$.name").value("카멜 울 코트"))
                .andExpect(jsonPath("$.type").value("outer"))
                .andExpect(jsonPath("$.warm").value("warm"));

        // AI 세부값 5(한겨울)를 넣은 뒤 같은 단계(warm)로 다시 저장해도 5가 유지된다
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"warm\":\"warm\",\"warmScore\":5}"))
                .andExpect(jsonPath("$.warmScore").value(5));
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"warm\":\"warm\",\"name\":\"롱 패딩\"}"))
                .andExpect(jsonPath("$.warmScore").value(5))
                .andExpect(jsonPath("$.name").value("롱 패딩"));

        // 단계를 바꾸면 그 단계 기본값
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"warm\":\"medium\"}"))
                .andExpect(jsonPath("$.warm").value("medium"))
                .andExpect(jsonPath("$.warmScore").value(3));

        // 빈 이름, 잘못된 색은 거절
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"  \",\"color\":\"남색\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.name").exists())
                .andExpect(jsonPath("$.fieldErrors.color").exists());
    }

    @Test
    void 사진은_dataURL로_보내면_파일로_저장하고_주소로_돌려준다() throws Exception {
        String token = signup("photographer");
        MvcResult created = mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(COAT.replace("\"grip\":false", "\"grip\":false,\"photo\":\"" + PNG_DATA_URL + "\"")))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.photo").value(startsWith("http://localhost:8080/uploads/")))
                .andReturn();
        JsonNode body = objectMapper.readTree(created.getResponse().getContentAsString());
        long id = body.get("id").asLong();
        String photo = body.get("photo").asText();

        // 받은 주소를 그대로 다시 보내도 같은 사진 유지 (수정 화면에서 전체 저장할 때)
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"photo\":\"" + photo + "\"}"))
                .andExpect(jsonPath("$.photo").value(photo));

        // 빈 문자열은 사진 지우기
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"photo\":\"\"}"))
                .andExpect(jsonPath("$.photo").doesNotExist());

        // 다른 사이트 주소나 이미지가 아닌 데이터는 거절
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"photo\":\"https://evil.example/a.jpg\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PHOTO"));
        mvc.perform(patch("/api/clothes/" + id).header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"photo\":\"data:text/html;base64,PGgxPg==\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PHOTO"));
    }

    @Test
    void 잘못된_입력은_필드별_에러() throws Exception {
        String token = signup("validator");
        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(COAT.replace("#C19A6B", "카멜").replace("카멜 울 코트", "가".repeat(61))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors.color").exists())
                .andExpect(jsonPath("$.fieldErrors.name").exists());

        // 60자까지는 된다 (AL-06)
        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT.replace("카멜 울 코트", "가".repeat(60))))
                .andExpect(status().isCreated());

        // 없는 값 (예전 값 minimal, 대문자는 허용)
        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT.replace("\"formal\"", "\"minimal\"")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
        mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT.replace("\"outer\"", "\"OUTER\"")))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.type").value("outer"));
        mvc.perform(get("/api/clothes").param("type", "hat").header("Authorization", "Bearer " + token))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 이미지_업로드() throws Exception {
        String token = signup("uploader");
        var jpg = new MockMultipartFile("file", "coat.jpg", "image/jpeg", new byte[]{1, 2, 3});
        mvc.perform(multipart("/api/clothes/image").file(jpg).header("Authorization", "Bearer " + token))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.photo").value(startsWith("http://localhost:8080/uploads/")));

        var txt = new MockMultipartFile("file", "a.txt", "text/plain", new byte[]{1});
        mvc.perform(multipart("/api/clothes/image").file(txt).header("Authorization", "Bearer " + token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_IMAGE"));
    }

    private long createCoat(String token) throws Exception {
        MvcResult created = mvc.perform(post("/api/clothes").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(COAT))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(created.getResponse().getContentAsString()).get("id").asLong();
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
