package com.ondo.closet.image;

import com.ondo.closet.global.config.AppProperties;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import org.springframework.stereotype.Component;

import java.util.Base64;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 옷의 photo 값 처리 (AL-05, AL-08).
 * - 받을 때: dataURL(data:image/jpeg;base64,...)이면 파일로 저장하고, 서버 사진 주소면 그대로 쓴다. DB에는 "/uploads/..." 만 저장.
 * - 줄 때: "/uploads/..." 앞에 서버 주소를 붙여 전체 주소로 돌려준다. 프론트는 img.src 에 바로 넣으면 된다.
 */
@Component
public class PhotoService {

    /** dataURL 로 받는 사진 한 장의 최대 크기 (프론트는 700px 로 줄여서 보낸다) */
    public static final int MAX_DATA_URL_BYTES = 3 * 1024 * 1024;

    private static final Pattern DATA_URL = Pattern.compile("^data:(image/(?:jpeg|jpg|png|webp));base64,(.+)$", Pattern.DOTALL);
    private static final Pattern STORED = Pattern.compile("^/uploads/[A-Za-z0-9._-]+$");
    private static final Map<String, String> EXTENSION = Map.of(
            "image/jpeg", "jpg", "image/jpg", "jpg", "image/png", "png", "image/webp", "webp");

    private final ImageStorage imageStorage;
    private final String publicBaseUrl;

    public PhotoService(ImageStorage imageStorage, AppProperties props) {
        this.imageStorage = imageStorage;
        String base = props.storage().publicBaseUrl();
        this.publicBaseUrl = base == null ? "" : base.replaceAll("/+$", "");
    }

    /** 요청의 photo → DB 에 저장할 값 ("/uploads/..." 또는 null). 빈 문자열은 사진 지우기 */
    public String store(String photo) {
        if (photo == null || photo.isBlank()) {
            return null;
        }
        String value = photo.trim();
        if (value.startsWith("data:")) {
            return saveDataUrl(value);
        }
        if (!publicBaseUrl.isEmpty() && value.startsWith(publicBaseUrl + "/uploads/")) {
            value = value.substring(publicBaseUrl.length());
        }
        if (STORED.matcher(value).matches()) {
            return value;
        }
        throw new ApiException(ErrorCode.INVALID_PHOTO);
    }

    /** DB 값 → 응답용 전체 주소 */
    public String publicUrl(String stored) {
        if (stored == null || stored.isBlank()) {
            return null;
        }
        return stored.startsWith("/") ? publicBaseUrl + stored : stored;
    }

    private String saveDataUrl(String dataUrl) {
        Matcher m = DATA_URL.matcher(dataUrl);
        if (!m.matches()) {
            throw new ApiException(ErrorCode.INVALID_PHOTO);
        }
        String base64 = m.group(2);
        // base64 길이로 먼저 걸러서 큰 데이터를 디코딩하지 않는다
        if ((long) base64.length() * 3 / 4 > MAX_DATA_URL_BYTES + 3) {
            throw new ApiException(ErrorCode.PHOTO_TOO_LARGE);
        }
        byte[] bytes;
        try {
            bytes = Base64.getMimeDecoder().decode(base64);
        } catch (IllegalArgumentException e) {
            throw new ApiException(ErrorCode.INVALID_PHOTO);
        }
        if (bytes.length == 0) {
            throw new ApiException(ErrorCode.INVALID_PHOTO);
        }
        if (bytes.length > MAX_DATA_URL_BYTES) {
            throw new ApiException(ErrorCode.PHOTO_TOO_LARGE);
        }
        return imageStorage.saveBytes(bytes, EXTENSION.get(m.group(1)));
    }
}
