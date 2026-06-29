package com.bank.stageonecode;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@SpringBootApplication(scanBasePackages = "com")
@EntityScan(basePackages = {
        "com.organization",
        "com.employee",
        "com.project",
        "com.indicator",
        "com.task",
        "com.performance",
        "com.points",
        "com.auth",
        "com.decomposition",
        "com.miniapp.practice.model"
})
@EnableJpaRepositories(basePackages = {
        "com.organization",
        "com.employee",
        "com.project",
        "com.indicator",
        "com.task",
        "com.performance",
        "com.points",
        "com.auth",
        "com.decomposition",
        "com.miniapp.practice.repository"
})
public class StageOneCodeApplication {

    public static void main(String[] args) {
        SpringApplication.run(StageOneCodeApplication.class, args);
    }

}
