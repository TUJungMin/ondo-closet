package com.ondo.closet.ai;

import com.ondo.closet.clothes.Category;
import com.ondo.closet.clothes.Style;

import java.util.Map;

/**
 * AI 서버의 한글 값 → 백엔드 enum.
 * 백엔드에 대응하는 값이 없으면 null 을 돌려주고, 화면에서 사용자가 직접 고르게 한다.
 * (팀에서 데이터 형식을 확정하면 이 표만 고치면 된다)
 */
public final class AiValueMapper {

    private static final Map<String, Category> CATEGORY = Map.of(
            "상의", Category.TOP,
            "바지", Category.PANTS,
            "스커트", Category.SKIRT,
            "겉옷", Category.OUTER,
            "신발", Category.SHOES);

    // AI 의 '스트릿', '페미닌' 은 백엔드 스타일 목록에 없어 매핑하지 않는다
    private static final Map<String, Style> STYLE = Map.of(
            "캐주얼", Style.CASUAL,
            "포멀", Style.FORMAL,
            "스포티", Style.SPORTY,
            "미니멀", Style.MINIMAL);

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
}
