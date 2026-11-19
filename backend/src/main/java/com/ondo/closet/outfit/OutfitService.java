package com.ondo.closet.outfit;

import com.ondo.closet.ai.AiServerClient;
import com.ondo.closet.ai.AiValueMapper;
import com.ondo.closet.ai.dto.AiRecommend;
import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Clothes;
import com.ondo.closet.clothes.ClothesService;
import com.ondo.closet.clothes.Style;
import com.ondo.closet.global.error.ApiException;
import com.ondo.closet.global.error.ErrorCode;
import com.ondo.closet.image.PhotoService;
import com.ondo.closet.outfit.dto.RecommendRequest;
import com.ondo.closet.outfit.dto.RecommendResponse;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * 코디 추천. 계산은 AI 서버(/ai/recommend, 준호 님 엔진)가 하고, 백엔드는 형식 변환과 아래 두 가지를 맡는다.
 * - 고정 옷이 없으면(AL-11) 날씨에 맞는 상의 최대 5벌을 차례로 고정해 AI를 부르고, 점수가 높은 조합을 고른다.
 * - 선호 스타일이 있으면(AL-13) AI 후보를 넉넉히 받아, 스타일이 맞는 조합을 앞으로 올린다.
 */
@Service
public class OutfitService {

    static final int DEFAULT_TOP_K = 3;
    static final int MAX_AUTO_PINS = 5;
    /** 조합의 옷이 모두 선호 스타일일 때 더하는 점수 (AI 점수 0~100 기준) */
    static final double PREFERRED_STYLE_BONUS = 10.0;

    private final ClothesService clothesService;
    private final AiServerClient aiServerClient;
    private final PhotoService photoService;

    public OutfitService(ClothesService clothesService, AiServerClient aiServerClient, PhotoService photoService) {
        this.clothesService = clothesService;
        this.aiServerClient = aiServerClient;
        this.photoService = photoService;
    }

    public RecommendResponse recommend(Long userId, RecommendRequest request) {
        List<Clothes> closet = clothesService.findAllEntities(userId);
        if (closet.isEmpty()) {
            throw new ApiException(ErrorCode.EMPTY_CLOSET);
        }
        Map<Long, Clothes> byId = closet.stream().collect(Collectors.toMap(Clothes::getId, Function.identity()));

        boolean autoPinned = request.pinnedId() == null;
        List<Long> pins;
        if (autoPinned) {
            pins = autoPins(closet, request.weather());
        } else if (byId.containsKey(request.pinnedId())) {
            pins = List.of(request.pinnedId());
        } else {
            throw new ApiException(ErrorCode.CLOTHES_NOT_FOUND);
        }

        Set<Style> preferred = request.preferredStyles() == null ? Set.of()
                : request.preferredStyles().stream().filter(s -> s != null).collect(Collectors.toCollection(LinkedHashSet::new));
        int topK = request.topK() == null ? DEFAULT_TOP_K : request.topK();
        int askK = preferred.isEmpty() ? topK : Math.min(10, Math.max(topK * 2, 6));

        // 같은 옷 조합이 여러 고정 옷에서 나오면 점수가 높은 쪽만 남긴다
        Map<String, Candidate> candidates = new LinkedHashMap<>();
        AiRecommend.Context context = null;
        for (Long pin : pins) {
            AiRecommend.Result result = aiServerClient.recommend(toAiRequest(closet, pin, request, askK));
            if (context == null) {
                context = result.context();
            }
            List<String> warnings = result.warnings() == null ? List.of() : result.warnings();
            if (result.recommendations() == null) {
                continue;
            }
            for (AiRecommend.Recommendation r : result.recommendations()) {
                Candidate c = new Candidate(r, warnings, bonus(r, byId, preferred));
                candidates.merge(key(r), c, (a, b) -> a.r().score() >= b.r().score() ? a : b);
            }
        }

        List<Candidate> ranked = candidates.values().stream()
                .sorted(Comparator.comparingDouble(Candidate::total).reversed())
                .limit(topK)
                .toList();

        List<RecommendResponse.Recommendation> recommendations = new ArrayList<>();
        for (int i = 0; i < ranked.size(); i++) {
            recommendations.add(toRecommendation(i + 1, ranked.get(i), byId, preferred));
        }
        double apparent = context == null ? request.weather().tempC() : context.apparentTempC();
        double effective = context == null ? apparent : context.effectiveTempC();
        List<String> warnings = ranked.isEmpty() ? List.of() : ranked.get(0).warnings();
        return new RecommendResponse(recommendations, apparent, effective, autoPinned, warnings);
    }

    /**
     * 고정 옷이 없을 때 돌려 볼 후보. 상의(없으면 하의, 겉옷, 신발 순) 중
     * 오늘 기온에 맞는 보온성에 가깝고, 오래 안 입은 옷부터 최대 5벌.
     */
    static List<Long> autoPins(List<Clothes> closet, RecommendRequest.WeatherInput weather) {
        double feels = weather.feelsLikeC() != null ? weather.feelsLikeC() : weather.tempC();
        int target = feels >= 23 ? 1 : feels >= 17 ? 2 : feels >= 10 ? 3 : 4;
        List<Predicate<Clothes>> order = List.of(
                c -> c.getCategory() == Category.TOP,
                c -> c.getCategory().isBottom(),
                c -> c.getCategory() == Category.OUTER,
                c -> true);
        for (Predicate<Clothes> group : order) {
            List<Long> picked = closet.stream()
                    .filter(group)
                    .sorted(Comparator.<Clothes>comparingInt(c -> Math.abs(c.getWarmth() - target))
                            .thenComparing(Clothes::getLastWornAt, Comparator.nullsFirst(Comparator.<LocalDate>naturalOrder()))
                            .thenComparing(Clothes::getId))
                    .limit(MAX_AUTO_PINS)
                    .map(Clothes::getId)
                    .toList();
            if (!picked.isEmpty()) {
                return picked;
            }
        }
        return List.of();
    }

    private AiRecommend.Request toAiRequest(List<Clothes> closet, Long pinnedId, RecommendRequest request, int topK) {
        List<AiRecommend.Garment> wardrobe = closet.stream()
                .map(c -> {
                    String color = AiValueMapper.aiColor(c.getColor());
                    return new AiRecommend.Garment(c.getId(), c.getName(), AiValueMapper.korean(c.getCategory()),
                            color == null ? List.of() : List.of(color), c.getWarmth(),
                            AiValueMapper.korean(c.getStyle()), c.isWaterproof(), c.isGrip());
                })
                .toList();
        RecommendRequest.WeatherInput w = request.weather();
        AiRecommend.Weather weather = new AiRecommend.Weather(w.tempC(), w.feelsLikeC(), w.tempMinC(), w.tempMaxC(),
                (w.sky() == null ? Sky.CLEAR : w.sky()).korean(), w.precipProb(), w.windMs());
        Place place = request.place() == null ? Place.DAILY : request.place();
        return new AiRecommend.Request(wardrobe, pinnedId, weather, place.korean(), topK);
    }

    private static double bonus(AiRecommend.Recommendation r, Map<Long, Clothes> byId, Set<Style> preferred) {
        if (preferred.isEmpty() || r.items() == null || r.items().isEmpty()) {
            return 0;
        }
        long matched = r.items().stream()
                .map(item -> byId.get(item.garmentId()))
                .filter(c -> c != null && preferred.contains(c.getStyle()))
                .count();
        return PREFERRED_STYLE_BONUS * matched / r.items().size();
    }

    private static String key(AiRecommend.Recommendation r) {
        return r.items() == null ? "" : r.items().stream()
                .map(i -> String.valueOf(i.garmentId())).sorted().collect(Collectors.joining(","));
    }

    private RecommendResponse.Recommendation toRecommendation(int rank, Candidate candidate, Map<Long, Clothes> byId,
                                                              Set<Style> preferred) {
        AiRecommend.Recommendation r = candidate.r();
        List<RecommendResponse.Item> items = r.items() == null ? List.of() : r.items().stream()
                .map(item -> {
                    Clothes c = byId.get(item.garmentId());
                    return new RecommendResponse.Item(item.slot(), item.garmentId(),
                            c == null ? item.name() : c.getName(),
                            c == null ? AiValueMapper.category(item.category()) : c.getCategory(),
                            c == null ? null : c.getColor(),
                            c == null ? null : c.getStyle(),
                            c == null ? null : photoService.publicUrl(c.getImageUrl()),
                            item.pinned());
                })
                .toList();
        List<RecommendResponse.Basis> basis = new ArrayList<>(r.basis() == null ? List.of()
                : r.basis().stream().map(b -> new RecommendResponse.Basis(b.kind(), b.text())).toList());
        if (candidate.bonus() > 0) {
            String styles = items.stream().map(RecommendResponse.Item::style)
                    .filter(s -> s != null && preferred.contains(s)).distinct()
                    .map(AiValueMapper::korean).collect(Collectors.joining("·"));
            basis.add(new RecommendResponse.Basis("취향", "좋아하는 " + styles + " 스타일이 들어간 조합을 우선했어요."));
        }
        return new RecommendResponse.Recommendation(rank, r.score(), r.reason(), basis,
                r.breakdown() == null ? Map.of() : r.breakdown(), items);
    }

    private record Candidate(AiRecommend.Recommendation r, List<String> warnings, double bonus) {
        double total() {
            return r.score() + bonus;
        }
    }
}
