package com.ondo.closet;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class OndoClosetApplication {

    public static void main(String[] args) {
        SpringApplication.run(OndoClosetApplication.class, args);
    }
}
