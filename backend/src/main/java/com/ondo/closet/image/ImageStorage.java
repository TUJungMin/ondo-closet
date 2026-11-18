package com.ondo.closet.image;

import org.springframework.web.multipart.MultipartFile;

/**
 * 옷 사진 저장소. 지금은 로컬 디스크 구현(LocalImageStorage)만 있다.
 * 무료 호스팅은 재배포 시 디스크가 초기화될 수 있으므로, 배포 전에
 * Supabase Storage / Cloudflare R2 / S3 구현체를 추가해서 교체하는 것을 권장.
 */
public interface ImageStorage {

    /** 저장 후 브라우저에서 바로 쓸 수 있는 URL(또는 경로)을 돌려준다 */
    String save(MultipartFile file, String extension);
}
