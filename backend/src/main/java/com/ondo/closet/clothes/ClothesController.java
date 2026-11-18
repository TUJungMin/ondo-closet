package com.ondo.closet.clothes;

import com.ondo.closet.clothes.dto.ClothesRequest;
import com.ondo.closet.clothes.dto.ClothesResponse;
import com.ondo.closet.global.security.AuthUser;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/clothes")
public class ClothesController {

    private final ClothesService clothesService;

    public ClothesController(ClothesService clothesService) {
        this.clothesService = clothesService;
    }

    /** GET /api/clothes, GET /api/clothes?category=OUTER */
    @GetMapping
    public List<ClothesResponse> list(@AuthenticationPrincipal AuthUser user,
                                      @RequestParam(required = false) Category category) {
        return clothesService.list(user.userId(), category);
    }

    @GetMapping("/{id}")
    public ClothesResponse get(@AuthenticationPrincipal AuthUser user, @PathVariable Long id) {
        return clothesService.get(user.userId(), id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ClothesResponse create(@AuthenticationPrincipal AuthUser user,
                                  @Valid @RequestBody ClothesRequest request) {
        return clothesService.create(user.userId(), request);
    }

    @PutMapping("/{id}")
    public ClothesResponse update(@AuthenticationPrincipal AuthUser user, @PathVariable Long id,
                                  @Valid @RequestBody ClothesRequest request) {
        return clothesService.update(user.userId(), id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@AuthenticationPrincipal AuthUser user, @PathVariable Long id) {
        clothesService.delete(user.userId(), id);
    }
}
