package com.ondo.closet.clothes;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ClothesRepository extends JpaRepository<Clothes, Long> {

    List<Clothes> findAllByUserIdOrderByCreatedAtDesc(Long userId);

    List<Clothes> findAllByUserIdAndCategoryOrderByCreatedAtDesc(Long userId, Category category);

    /** 남의 옷을 id만 바꿔서 조회·수정하지 못하도록 항상 user_id와 함께 찾는다 */
    Optional<Clothes> findByIdAndUserId(Long id, Long userId);

    long countByUserId(Long userId);
}
