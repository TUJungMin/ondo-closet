package com.ondo.closet.ai;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;

import java.util.Map;

/**
 * AI 서버의 한글 값 ↔ 백엔드 enum.
 * 백엔드에 대응하는 값이 없으면 null 을 돌려주고, 화면에서 사용자가 직접 고르게 한다.
 */
public final class AiValueMapper {

    private static final Map<String, Category> CATEGORY = Map.of(
            "상의", Category.TOP,
            "바지", Category.PANTS,
            "스커트", Category.SKIRT,
            "겉옷", Category.OUTER,
            "신발", Category.SHOES);

    private static final Map<String, Style> STYLE = Map.of(
            "캐주얼", Style.CASUAL,
            "포멀", Style.FORMAL,
            "스포티", Style.SPORTY,
            "스트릿", Style.STREET,
            "페미닌", Style.FEMININE);

    // 예전 데이터처럼 색이 이름으로 들어온 경우 AI 이름표에 맞춘다
    private static final Map<String, String> COLOR_ALIAS = Map.ofEntries(
            Map.entry("화이트", "흰색"), Map.entry("하양", "흰색"), Map.entry("블랙", "검정"), Map.entry("검은색", "검정"),
            Map.entry("그레이", "회색"), Map.entry("크림", "아이보리"), Map.entry("브라운", "갈색"),
            Map.entry("네이비", "남색"), Map.entry("블루", "파랑"), Map.entry("파란색", "파랑"),
            Map.entry("라이트 블루", "하늘색"), Map.entry("그린", "초록"), Map.entry("옐로우", "노랑"),
            Map.entry("오렌지", "주황"), Map.entry("레드", "빨강"), Map.entry("와인", "버건디"),
            Map.entry("핑크", "분홍"), Map.entry("퍼플", "보라"), Map.entry("올리브", "카키"));

    private AiValueMapper() {
    }

    public static Category category(String korean) {
        return korean == null ? null : CATEGORY.get(korean.trim());
    }

    public static Style style(String korean) {
        return korean == null ? null : STYLE.get(korean.trim());
    }

    public static Integer warmth(Integer value) {
        return value != null && value >= 1 && value <= 5 ? value : null;
    }

    public static String korean(Category category) {
        return CATEGORY.entrySet().stream().filter(e -> e.getValue() == category)
                .map(Map.Entry::getKey).findFirst().orElseThrow();
    }

    public static String korean(Style style) {
        if (style == null) {
            return null;
        }
        return STYLE.entrySet().stream().filter(e -> e.getValue() == style)
                .map(Map.Entry::getKey).findFirst().orElseThrow();
    }

    /** 저장된 색(HEX 또는 이름) → AI 색 이름표의 이름 */
    public static String aiColor(String color) {
        if (color == null || color.isBlank()) {
            return null;
        }
        String trimmed = color.trim();
        if (ColorPalette.isHex(trimmed)) {
            return ColorPalette.nearestName(trimmed);
        }
        return COLOR_ALIAS.getOrDefault(trimmed, trimmed);
    }
}
