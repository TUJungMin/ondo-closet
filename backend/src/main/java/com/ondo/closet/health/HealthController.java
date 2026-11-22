package com.ondo.closet.health;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 배포 확인용. 무료 호스팅이 잠들지 않게 하는 핑(ping) 주소로도 쓴다. */
@RestController
public class HealthController {

    @GetMapping("/api/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
