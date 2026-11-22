package com.ondo.closet.outfit;

import com.ondo.closet.global.security.AuthUser;
import com.ondo.closet.outfit.dto.RecommendRequest;
import com.ondo.closet.outfit.dto.RecommendResponse;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/outfits")
public class OutfitController {

    private final OutfitService outfitService;

    public OutfitController(OutfitService outfitService) {
        this.outfitService = outfitService;
    }

    /** 옷 한 벌을 고정하고, 날씨·장소에 맞는 코디 조합을 추천받는다 */
    @PostMapping("/recommend")
    public RecommendResponse recommend(@AuthenticationPrincipal AuthUser user,
                                       @Valid @RequestBody RecommendRequest request) {
        return outfitService.recommend(user.userId(), request);
    }
}
