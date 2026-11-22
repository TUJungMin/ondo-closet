package com.ondo.closet.clothes;

import com.ondo.closet.clothes.dto.ClothesPatchRequest;
import com.ondo.closet.clothes.dto.ClothesRequest;
import com.ondo.closet.clothes.dto.ClothesResponse;
import com.ondo.closet.global.config.AppProperties;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import com.ondo.closet.image.PhotoService;
import com.ondo.closet.user.User;
import com.ondo.closet.user.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class ClothesService {

    private final ClothesRepository clothesRepository;
    private final UserRepository userRepository;
    private final PhotoService photoService;
    private final int maxItemsPerUser;

    public ClothesService(ClothesRepository clothesRepository, UserRepository userRepository,
                          PhotoService photoService, AppProperties props) {
        this.clothesRepository = clothesRepository;
        this.userRepository = userRepository;
        this.photoService = photoService;
        this.maxItemsPerUser = props.closet().maxItemsPerUser();
    }

    @Transactional(readOnly = true)
    public List<ClothesResponse> list(Long userId, Category type) {
        List<Clothes> items = type == null
                ? clothesRepository.findAllByUserIdOrderByCreatedAtDesc(userId)
                : clothesRepository.findAllByUserIdAndCategoryOrderByCreatedAtDesc(userId, type);
        return items.stream().map(this::toResponse).toList();
    }

    /** 추천·조합 계산 등 다른 서비스에서 엔티티 그대로 쓸 때 */
    @Transactional(readOnly = true)
    public List<Clothes> findAllEntities(Long userId) {
        return clothesRepository.findAllByUserIdOrderByCreatedAtDesc(userId);
    }

    @Transactional(readOnly = true)
    public ClothesResponse get(Long userId, Long clothesId) {
        return toResponse(find(userId, clothesId));
    }

    @Transactional
    public ClothesResponse create(Long userId, ClothesRequest r) {
        if (clothesRepository.countByUserId(userId) >= maxItemsPerUser) {
            throw new ApiException(ErrorCode.CLOSET_FULL);
        }
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ApiException(ErrorCode.USER_NOT_FOUND));
        ClothesSpec spec = new ClothesSpec(r.name(), r.type(), r.color(), r.material(),
                r.warm().resolve(r.warmScore()), r.style(), Boolean.TRUE.equals(r.water()),
                Boolean.TRUE.equals(r.grip()), photoService.store(r.photo()), Boolean.TRUE.equals(r.aiTagged()));
        return toResponse(clothesRepository.save(new Clothes(user, spec)));
    }

    /** PUT: 모든 필드를 다시 받는다. 보온성 단계가 그대로면 기존 1~5 세부값을 지킨다 */
    @Transactional
    public ClothesResponse update(Long userId, Long clothesId, ClothesRequest r) {
        Clothes c = find(userId, clothesId);
        Integer detail = r.warmScore() != null ? r.warmScore() : c.getWarmth();
        c.apply(new ClothesSpec(r.name(), r.type(), r.color(), r.material(), r.warm().resolve(detail), r.style(),
                Boolean.TRUE.equals(r.water()), Boolean.TRUE.equals(r.grip()), photoService.store(r.photo()),
                Boolean.TRUE.equals(r.aiTagged())));
        return toResponse(c);
    }

    /** PATCH: 보낸 값만 바꾼다 (AL-07) */
    @Transactional
    public ClothesResponse patch(Long userId, Long clothesId, ClothesPatchRequest r) {
        Clothes c = find(userId, clothesId);
        int warmth = c.getWarmth();
        if (r.warm() != null) {
            warmth = r.warm().resolve(r.warmScore() != null ? r.warmScore() : c.getWarmth());
        } else if (r.warmScore() != null) {
            warmth = r.warmScore();
        }
        c.apply(new ClothesSpec(
                r.name() != null ? r.name() : c.getName(),
                r.type() != null ? r.type() : c.getCategory(),
                r.color() != null ? r.color() : c.getColor(),
                r.material() != null ? r.material() : c.getMaterial(),
                warmth,
                r.style() != null ? r.style() : c.getStyle(),
                r.water() != null ? r.water() : c.isWaterproof(),
                r.grip() != null ? r.grip() : c.isGrip(),
                r.photo() != null ? photoService.store(r.photo()) : c.getImageUrl(),
                r.aiTagged() != null ? r.aiTagged() : c.isAiTagged()));
        return toResponse(c);
    }

    @Transactional
    public void delete(Long userId, Long clothesId) {
        clothesRepository.delete(find(userId, clothesId));
    }

    public ClothesResponse toResponse(Clothes c) {
        return ClothesResponse.from(c, photoService);
    }

    private Clothes find(Long userId, Long clothesId) {
        return clothesRepository.findByIdAndUserId(clothesId, userId)
                .orElseThrow(() -> new ApiException(ErrorCode.CLOTHES_NOT_FOUND));
    }
}
