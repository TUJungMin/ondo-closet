package com.ondo.closet.image;

import com.ondo.closet.global.config.AppProperties;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.UUID;

@Component
public class LocalImageStorage implements ImageStorage {

    private final Path root;

    public LocalImageStorage(AppProperties props) {
        this.root = Path.of(props.storage().localDir()).toAbsolutePath().normalize();
        try {
            Files.createDirectories(root);
        } catch (IOException e) {
            throw new UncheckedIOException("업로드 폴더를 만들 수 없습니다: " + root, e);
        }
    }

    @Override
    public String save(MultipartFile file, String extension) {
        // 원래 파일 이름은 쓰지 않고 무작위 이름으로 저장 (경로 조작·덮어쓰기 방지)
        String filename = UUID.randomUUID() + "." + extension;
        Path target = root.resolve(filename);
        try (InputStream in = file.getInputStream()) {
            Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            throw new UncheckedIOException("이미지 저장 실패", e);
        }
        return "/uploads/" + filename;
    }
}
