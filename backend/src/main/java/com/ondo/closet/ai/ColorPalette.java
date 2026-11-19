package com.ondo.closet.ai;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * AI 서버의 색 이름표(ai/ondo_ai/palette.py)와 같은 19색.
 * 백엔드는 색을 HEX(#RRGGBB)로 저장하고(AL-02), AI 추천에 보낼 때 가장 가까운 이름으로 바꾼다.
 * palette.py 의 견본이 바뀌면 여기도 같이 바꾼다.
 */
public final class ColorPalette {

    public static final Pattern HEX = Pattern.compile("^#[0-9a-fA-F]{6}$");

    private static final Map<String, List<String>> SWATCHES = new LinkedHashMap<>();

    static {
        SWATCHES.put("검정", List.of("#000000", "#151515", "#222222"));
        SWATCHES.put("흰색", List.of("#ffffff", "#f4f4f4"));
        SWATCHES.put("회색", List.of("#808080", "#a9a9a9", "#5a5a5a", "#c8c8c8", "#36454f"));
        SWATCHES.put("아이보리", List.of("#f3ecd9", "#efe6d0", "#faf3e0"));
        SWATCHES.put("베이지", List.of("#d9c4a1", "#c8b28e", "#e3d3b5", "#cdb99a"));
        SWATCHES.put("카멜", List.of("#c19a6b", "#b5834f", "#c68e4e"));
        SWATCHES.put("갈색", List.of("#6b4423", "#8b5a2b", "#5c4033", "#7b4b2a"));
        SWATCHES.put("카키", List.of("#6b6b3a", "#5a5f3c", "#78704a", "#4b5320"));
        SWATCHES.put("남색", List.of("#1f2a44", "#14213d", "#000080", "#23395d", "#2b3a55"));
        SWATCHES.put("파랑", List.of("#1e5aa8", "#0057b8", "#3a6ea5", "#4169e1", "#4a6a8a", "#5b7c99"));
        SWATCHES.put("하늘색", List.of("#87ceeb", "#a6c8e6", "#b5d3e7", "#9bb7d4"));
        SWATCHES.put("초록", List.of("#228b22", "#2e7d32", "#3c8d5a", "#1b5e20"));
        SWATCHES.put("민트", List.of("#98d8c8", "#a8e0d0"));
        SWATCHES.put("노랑", List.of("#f7d038", "#ffe066", "#e6b800", "#d4a72c"));
        SWATCHES.put("주황", List.of("#f28c28", "#ff7f32", "#e2711d"));
        SWATCHES.put("빨강", List.of("#d32f2f", "#c62828", "#e53935", "#b71c1c"));
        SWATCHES.put("버건디", List.of("#800020", "#6d1a2a", "#7b1e3a", "#5e1224"));
        SWATCHES.put("분홍", List.of("#f8bbd0", "#f48fb1", "#ffc0cb", "#e8739c"));
        SWATCHES.put("보라", List.of("#6a1b9a", "#7e57c2", "#8e44ad", "#b39ddb"));
    }

    private ColorPalette() {
    }

    public static boolean isHex(String value) {
        return value != null && HEX.matcher(value.trim()).matches();
    }

    public static boolean isName(String value) {
        return value != null && SWATCHES.containsKey(value.trim());
    }

    /** 이름의 대표 HEX (첫 번째 견본). 모르는 이름이면 null */
    public static String hexOf(String name) {
        List<String> swatches = name == null ? null : SWATCHES.get(name.trim());
        return swatches == null ? null : swatches.get(0);
    }

    /** HEX 와 가장 가까운 색 이름 (Lab 색 공간 거리) */
    public static String nearestName(String hex) {
        double[] target = lab(hex);
        String best = null;
        double bestDistance = Double.MAX_VALUE;
        for (Map.Entry<String, List<String>> entry : SWATCHES.entrySet()) {
            for (String swatch : entry.getValue()) {
                double d = distance(target, lab(swatch));
                if (d < bestDistance) {
                    bestDistance = d;
                    best = entry.getKey();
                }
            }
        }
        return best;
    }

    private static double distance(double[] a, double[] b) {
        double dl = a[0] - b[0], da = a[1] - b[1], db = a[2] - b[2];
        return dl * dl + da * da + db * db;
    }

    /** sRGB HEX → CIE Lab (D65) */
    private static double[] lab(String hex) {
        int rgb = Integer.parseInt(hex.trim().substring(1), 16);
        double r = linear(((rgb >> 16) & 0xff) / 255.0);
        double g = linear(((rgb >> 8) & 0xff) / 255.0);
        double b = linear((rgb & 0xff) / 255.0);
        double x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
        double y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        double z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
        double fx = f(x), fy = f(y), fz = f(z);
        return new double[]{116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)};
    }

    private static double linear(double c) {
        return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    }

    private static double f(double t) {
        return t > 216.0 / 24389 ? Math.cbrt(t) : (24389.0 / 27 * t + 16) / 116;
    }
}
