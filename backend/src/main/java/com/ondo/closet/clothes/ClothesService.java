package com.ondo.closet.clothes;

import com.ondo.closet.clothes.dto.ClothesRequest;
import com.ondo.closet.clothes.dto.ClothesResponse;
import com.ondo.closet.global.config.AppProperties;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import com.ondo.closet.user.User;
import com.ondo.closet.user.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class ClothesService {

    private final ClothesRepository clothesRepository;
    private final UserRepository userRepository;
    private final int maxItemsPerUser;

    public ClothesService(ClothesRepository clothesRepository, UserRepository userRepository,
                          AppProperties props) {
        this.clothesRepository = clothesRepository;
        this.userRepository = userRepository;
        this.maxItemsPerUser = props.closet().maxItemsPerUser();
    }

    @Transactional(readOnly = true)
    public List<ClothesResponse> list(Long userId, Category category) {
        List<Clothes> items = category == null
                ? clothesRepository.findAllByUserIdOrderByCreatedAtDesc(userId)
                : clothesRepository.findAllByUserIdAndCategoryOrderByCreatedAtDesc(userId, category);
        return items.stream().map(ClothesResponse::from).toList();
    }

    /** 추천·조합 계산 등 다른 서비스에서 엔티티 그대로 쓸 때 */
    @Transactional(readOnly = true)
    public List<Clothes> findAllEntities(Long userId) {
        return clothesRepository.findAllByUserIdOrderByCreatedAtDesc(userId);
    }

    @Transactional(readOnly = true)
    public ClothesResponse get(Long userId, Long clothesId) {
        return ClothesResponse.from(find(userId, clothesId));
    }

    @Transactional
    public ClothesResponse create(Long userId, ClothesRequest request) {
        if (clothesRepository.countByUserId(userId) >= maxItemsPerUser) {
            throw new ApiException(ErrorCode.CLOSET_FULL);
        }
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ApiException(ErrorCode.USER_NOT_FOUND));
        Clothes saved = clothesRepository.save(new Clothes(user, request.toSpec()));
        return ClothesResponse.from(saved);
    }

    @Transactional
    public ClothesResponse update(Long userId, Long clothesId, ClothesRequest request) {
        Clothes clothes = find(userId, clothesId);
        clothes.apply(request.toSpec());
        return ClothesResponse.from(clothes);
    }

    @Transactional
    public void delete(Long userId, Long clothesId) {
        clothesRepository.delete(find(userId, clothesId));
    }

    private Clothes find(Long userId, Long clothesId) {
        return clothesRepository.findByIdAndUserId(clothesId, userId)
                .orElseThrow(() -> new ApiException(ErrorCode.CLOTHES_NOT_FOUND));
    }
}
