package pe.edu.utec.manka.service;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pe.edu.utec.manka.dto.RecommendationBreakdownDto;
import pe.edu.utec.manka.dto.RecommendationRequestDto;
import pe.edu.utec.manka.dto.RecommendationResponseDto;
import pe.edu.utec.manka.entity.HistorialCocina;
import pe.edu.utec.manka.entity.Ingrediente;
import pe.edu.utec.manka.entity.Plato;
import pe.edu.utec.manka.entity.Usuario;
import pe.edu.utec.manka.exception.BusinessRuleException;
import pe.edu.utec.manka.exception.ResourceNotFoundException;
import pe.edu.utec.manka.recommendation.RecommendationContext;
import pe.edu.utec.manka.recommendation.RecommendationEngine;
import pe.edu.utec.manka.recommendation.RecommendationResult;
import pe.edu.utec.manka.repository.HistorialCocinaRepository;
import pe.edu.utec.manka.repository.IngredienteRepository;
import pe.edu.utec.manka.repository.PlatoRepository;
import pe.edu.utec.manka.repository.IngredienteLineaOriginalRepository;
import pe.edu.utec.manka.entity.IngredienteLineaOriginal;
import pe.edu.utec.manka.repository.UsuarioRepository;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class RecommendationService {
    private final UsuarioRepository usuarioRepository;
    private final IngredienteRepository ingredienteRepository;
    private final PlatoRepository platoRepository;
    private final HistorialCocinaRepository historialRepository;
    private final RecommendationEngine recommendationEngine;
    private final IngredienteLineaOriginalRepository originalRepository;

    public RecommendationService(UsuarioRepository usuarioRepository,
                                 IngredienteRepository ingredienteRepository,
                                 PlatoRepository platoRepository,
                                 HistorialCocinaRepository historialRepository,
                                 RecommendationEngine recommendationEngine,
                                 IngredienteLineaOriginalRepository originalRepository) {
        this.usuarioRepository = usuarioRepository;
        this.ingredienteRepository = ingredienteRepository;
        this.platoRepository = platoRepository;
        this.historialRepository = historialRepository;
        this.recommendationEngine = recommendationEngine;
        this.originalRepository = originalRepository;
    }

    @Transactional(readOnly = true)
    public Page<RecommendationResponseDto> recommend(String email, RecommendationRequestDto request) {
        Usuario user = usuarioRepository.findWithDespensaByEmail(email)
                .orElseThrow(() -> new ResourceNotFoundException("Authenticated user not found"));

        Set<Ingrediente> availableIngredients = resolveIngredients(request, user);
        if (availableIngredients.isEmpty()) {
            throw new BusinessRuleException("Add at least one ingredient or save ingredients in your pantry first");
        }

        Set<Long> availableIds = availableIngredients.stream()
                .map(Ingrediente::getId).collect(java.util.stream.Collectors.toSet());
        Set<Long> parentIds = availableIngredients.stream()
                .map(Ingrediente::getParent)
                .filter(java.util.Objects::nonNull)
                .map(Ingrediente::getId).collect(java.util.stream.Collectors.toSet());
        // SQL IN vacío puede fallar en algunos dialectos; -1 no coincide con ningún ID real.
        if (parentIds.isEmpty()) parentIds.add(-1L);
        List<Long> candidateIds = platoRepository.findCandidateIds(
                request.getAvailableMinutes(), availableIds, parentIds);
        List<Plato> candidates = new ArrayList<>();
        // Evitar un IN gigantesco. Mantiene los candidatos válidos sin cargar todo el catálogo.
        for (int offset = 0; offset < candidateIds.size(); offset += 250) {
            candidates.addAll(platoRepository.findDetailedByIds(
                    candidateIds.subList(offset, Math.min(offset + 250, candidateIds.size()))));
        }
        List<HistorialCocina> recentHistory = historialRepository.findRecentByUserId(
                user.getId(), LocalDateTime.now().minusDays(30));

        RecommendationContext context = new RecommendationContext(
                availableIngredients,
                request.getAvailableMinutes(),
                recentHistory
        );

        int size = request.getLimit() == null ? 10 : request.getLimit();
        int page = request.getPage() == null ? 0 : request.getPage();
        PageRequest pageable = PageRequest.of(page, size);

        // El total se calcula ANTES de extraer la página.
        List<RecommendationResult> ranked = recommendationEngine.rankAll(candidates, context);
        int total = ranked.size();
        long start = (long) page * size;
        if (start >= total) {
            return new PageImpl<>(List.of(), pageable, total);
        }
        int from = (int) start;
        int to = Math.min(from + size, total);
        List<RecommendationResponseDto> content = ranked.subList(from, to).stream()
                .map(result -> toResponse(result, request.getAvailableMinutes(), availableIds))
                .toList();
        return new PageImpl<>(content, pageable, total);
    }

    private Set<Ingrediente> resolveIngredients(RecommendationRequestDto request, Usuario user) {
        if (request.getIngredientIds() == null || request.getIngredientIds().isEmpty()) {
            return new HashSet<>(user.getDespensa());
        }

        List<Ingrediente> ingredients = ingredienteRepository.findAllById(request.getIngredientIds());
        if (ingredients.size() != request.getIngredientIds().size()) {
            throw new BusinessRuleException("One or more ingredientIds do not exist");
        }
        return new HashSet<>(ingredients);
    }

    private RecommendationResponseDto toResponse(RecommendationResult result, int availableMinutes, Set<Long> availableIds) {
        RecommendationResponseDto response = new RecommendationResponseDto();
        Plato dish = result.getPlato();
        response.setPlatoId(dish.getId());
        response.setNombre(dish.getNombre());
        response.setTiempoPreparacion(dish.getTiempoPreparacion());
        response.setDificultad(dish.getDificultad());
        response.setScore(result.getScoring().getFinalScore());
        response.setIngredientCoveragePercent(result.getCoveragePercent());
        response.setMatchedIngredients(result.getMatchedIngredients());
        response.setTotalIngredients(result.getTotalIngredients());
        response.setMissingIngredients(result.getMissingIngredients());
        response.setBreakdown(toBreakdown(result.getScoring().getBreakdown()));
        response.setReasons(buildReasons(result, availableMinutes));
        response.setPresentacionesCoincidentes(originalRepository
            .findByPlatoIdAndIngredienteIdInOrderByPosicionAsc(dish.getId(), availableIds)
            .stream().map(IngredienteLineaOriginal::getTextoOriginal).distinct().toList());
        return response;
    }

    private RecommendationBreakdownDto toBreakdown(Map<String, Double> scores) {
        RecommendationBreakdownDto dto = new RecommendationBreakdownDto();
        dto.setIngredientCoverage(scores.getOrDefault("ingredientCoverage", 0.0));
        dto.setTime(scores.getOrDefault("time", 0.0));
        dto.setProteinVariety(scores.getOrDefault("proteinVariety", 0.0));
        dto.setRepetition(scores.getOrDefault("repetition", 0.0));
        dto.setPopularity(scores.getOrDefault("popularity", 0.0));
        return dto;
    }

    private List<String> buildReasons(RecommendationResult result, int availableMinutes) {
        List<String> reasons = new ArrayList<>();
        reasons.add("Usas " + result.getMatchedIngredients() + " de " + result.getTotalIngredients() + " ingredientes necesarios");
        reasons.add("Listo en " + result.getPlato().getTiempoPreparacion() + " min; entra en tus " + availableMinutes + " min disponibles");

        if (result.getMissingIngredients().isEmpty()) {
            reasons.add("Tienes el 100% de los ingredientes necesarios");
        } else {
            reasons.add("Tienes el " + result.getCoveragePercent() + "% de lo necesario; faltan " + result.getMissingIngredients().size() + " ingredientes");
        }

        double repetition = result.getScoring().getBreakdown().getOrDefault("repetition", 100.0);
        if (repetition == 0.0) {
            reasons.add("Lo cocinaste en los últimos 7 días, por eso recibe penalización por repetición");
        } else {
            reasons.add("No lo cocinaste en los últimos 7 días");
        }
        return reasons;
    }
}
