package pe.edu.utec.manka.controller;

import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import pe.edu.utec.manka.dto.RecommendationRequestDto;
import pe.edu.utec.manka.dto.RecommendationResponseDto;
import pe.edu.utec.manka.service.RecommendationService;


@RestController
@RequestMapping("/recommendations")
public class RecommendationController {
    private final RecommendationService recommendationService;

    public RecommendationController(RecommendationService recommendationService) {
        this.recommendationService = recommendationService;
    }

    @PostMapping
    public Page<RecommendationResponseDto> recommend(@AuthenticationPrincipal Jwt jwt,
                                                       @Valid @RequestBody RecommendationRequestDto request) {
        return recommendationService.recommend(jwt.getSubject(), request);
    }
}
