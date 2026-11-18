package com.ondo.closet.image;

import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

/**
 * 옷 사진 업로드 → URL 반환. 흐름:
 * 1) POST /api/clothes/image (form-data, file=사진) → {"imageUrl":"/uploads/xxx.jpg"}
 * 2) (다음 단계) POST /api/clothes/tag 로 AI 자동 태깅
 * 3) POST /api/clothes 에 imageUrl과 속성을 함께 저장
 */
@RestController
public class ImageController {

    private static final Map<String, String> ALLOWED = Map.of(
            MediaType.IMAGE_JPEG_VALUE, "jpg",
            MediaType.IMAGE_PNG_VALUE, "png",
            "image/webp", "webp");

    private final ImageStorage imageStorage;

    public ImageController(ImageStorage imageStorage) {
        this.imageStorage = imageStorage;
    }

    @PostMapping(value = "/api/clothes/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, String> upload(@RequestParam("file") MultipartFile file) {
        String extension = file.isEmpty() ? null : ALLOWED.get(file.getContentType());
        if (extension == null) {
            throw new ApiException(ErrorCode.INVALID_IMAGE);
        }
        return Map.of("imageUrl", imageStorage.save(file, extension));
    }
}
