package com.ondo.closet.demo;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ondo.closet.clothes.Clothes;
import com.ondo.closet.clothes.ClothesRepository;
import com.ondo.closet.clothes.ClothesSpec;
import com.ondo.closet.user.User;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.List;

/**
 * 게스트 계정에 넣을 샘플 옷장. 내용은 src/main/resources/demo/demo-closet.json 에서 수정한다.
 * 샘플 옷 사진이 준비되면 각 항목의 imageUrl 을 채우면 된다.
 */
@Component
public class DemoClosetSeeder {

    private final ClothesRepository clothesRepository;
    private final List<ClothesSpec> items;

    public DemoClosetSeeder(ClothesRepository clothesRepository, ObjectMapper objectMapper) {
        this.clothesRepository = clothesRepository;
        try (InputStream in = new ClassPathResource("demo/demo-closet.json").getInputStream()) {
            this.items = List.copyOf(objectMapper.readValue(in, new TypeReference<List<ClothesSpec>>() {
            }));
        } catch (IOException e) {
            throw new UncheckedIOException("demo-closet.json 을 읽을 수 없습니다.", e);
        }
    }

    public void seed(User user) {
        clothesRepository.saveAll(items.stream().map(spec -> new Clothes(user, spec)).toList());
    }

    public int size() {
        return items.size();
    }
}
