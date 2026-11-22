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
 * 옷 사진 파일 업로드 → 사진 주소 반환: POST /api/clothes/image (form-data, file=사진) → {"photo":"http://.../uploads/xxx.jpg"}
 * 옷 저장 때 photo 에 dataURL 을 바로 넣어도 되므로(AL-08), 이 API 는 파일을 따로 올리고 싶을 때만 쓴다.
 */
@RestController
public class ImageController {

    private static final Map<String, String> ALLOWED = Map.of(
            MediaType.IMAGE_JPEG_VALUE, "jpg",
            MediaType.IMAGE_PNG_VALUE, "png",
            "image/webp", "webp");

    private final ImageStorage imageStorage;
    private final PhotoService photoService;

    public ImageController(ImageStorage imageStorage, PhotoService photoService) {
        this.imageStorage = imageStorage;
        this.photoService = photoService;
    }

    @PostMapping(value = "/api/clothes/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, String> upload(@RequestParam("file") MultipartFile file) {
        String extension = file.isEmpty() ? null : ALLOWED.get(file.getContentType());
        if (extension == null) {
            throw new ApiException(ErrorCode.INVALID_IMAGE);
        }
        return Map.of("photo", photoService.publicUrl(imageStorage.save(file, extension)));
    }
}
