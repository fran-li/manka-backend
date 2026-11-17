package pe.edu.utec.manka.service;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pe.edu.utec.manka.dto.PlatoIngredienteResponseDto;
import pe.edu.utec.manka.dto.PlatoResponseDto;
import pe.edu.utec.manka.entity.Plato;
import pe.edu.utec.manka.entity.PlatoIngrediente;
import pe.edu.utec.manka.exception.ResourceNotFoundException;
import pe.edu.utec.manka.repository.PlatoRepository;
import pe.edu.utec.manka.repository.IngredienteLineaOriginalRepository;
import pe.edu.utec.manka.entity.IngredienteLineaOriginal;
import java.util.List;

@Service
public class PlatoService {
    private final PlatoRepository platoRepository;
    private final IngredienteLineaOriginalRepository originalRepository;
    public PlatoService(PlatoRepository platoRepository, IngredienteLineaOriginalRepository originalRepository) {
        this.platoRepository = platoRepository;
        this.originalRepository = originalRepository;
    }

    // Compatibilidad: GET /dishes sin paginar conserva el formato anterior (array JSON).
    // Para el catálogo grande usar GET /dishes/page.
    @Transactional(readOnly = true)
    public List<PlatoResponseDto> search(String search, Integer maxMinutes) {
        if (maxMinutes != null) {
            List<Plato> dishes = platoRepository.findCandidates(maxMinutes);
            if (search != null && !search.isBlank()) {
                String term = search.trim().toLowerCase(java.util.Locale.ROOT);
                dishes = dishes.stream().filter(d -> d.getNombre().toLowerCase(java.util.Locale.ROOT).contains(term)).toList();
            }
            return dishes.stream().map(d -> toResponse(d, true)).toList();
        }
        List<Plato> dishes = search != null && !search.isBlank()
                ? platoRepository.findByNombreContainingIgnoreCaseOrderByNombreAsc(search.trim())
                : platoRepository.findAll();
        return dishes.stream().map(d -> toResponse(d, true)).toList();
    }

    @Transactional(readOnly = true)
    public Page<PlatoResponseDto> searchPage(String search, Integer maxMinutes, int page, int size) {
        if (page < 0 || size < 1 || size > 100 || (maxMinutes != null && maxMinutes < 1)) {
            throw new IllegalArgumentException("page >= 0, size 1..100 y maxMinutes positivo");
        }
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.ASC, "id"));
        boolean hasTerm = search != null && !search.isBlank();
        Page<Plato> result;
        if (!hasTerm && maxMinutes == null) {
            result = platoRepository.findAll(pageable);
        } else if (!hasTerm) {
            result = platoRepository.findByTiempoPreparacionLessThanEqual(maxMinutes, pageable);
        } else if (maxMinutes == null) {
            result = platoRepository.findByNombreContainingIgnoreCase(search.trim(), pageable);
        } else {
            result = platoRepository.findByNombreContainingIgnoreCaseAndTiempoPreparacionLessThanEqual(
                    search.trim(), maxMinutes, pageable);
        }
        // Sin ingredientes para mantener la paginación ligera. Los detalles están en GET /dishes/{id}.
        return result.map(dish -> toResponse(dish, false));
    }

    @Transactional(readOnly = true)
    public PlatoResponseDto getById(Long id) {
        Plato dish = platoRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Dish not found"));
        PlatoResponseDto response = toResponse(dish, true);
        response.setIngredientesCsv(originalRepository.findByPlatoIdOrderByPosicionAsc(dish.getId())
            .stream().map(IngredienteLineaOriginal::getTextoOriginal).toList());
        return response;
    }

    public PlatoResponseDto toResponse(Plato dish, boolean includeIngredients) {
        PlatoResponseDto response = new PlatoResponseDto();
        response.setId(dish.getId());
        response.setNombre(dish.getNombre());
        response.setTiempoPreparacion(dish.getTiempoPreparacion());
        response.setDificultad(dish.getDificultad());
        response.setPopularidad(dish.getPopularidad());
        response.setPreparacion(dish.getPreparacion());
        response.setSourceId(dish.getSourceId());
        response.setSourceUrl(dish.getSourceUrl());
        response.setCountry(dish.getCountry());
        response.setServings(dish.getServings());
        response.setMealType(dish.getMealType());
        response.setRatingAverage(dish.getRatingAverage());
        response.setRatingVotes(dish.getRatingVotes());
        response.setDurationEstimated(dish.getDurationEstimated());
        response.setDifficultyEstimated(dish.getDifficultyEstimated());
        if (dish.getCategoriaProteina() != null) response.setCategoriaProteina(dish.getCategoriaProteina().getNombre());
        if (includeIngredients) {
            response.setIngredientes(dish.getIngredientes().stream().map(this::ingredientToResponse).toList());
            response.setProteinSources(dish.getProteinSources().stream().map(s -> s.getName()).sorted().toList());
            response.setTags(dish.getTags().stream().map(t -> t.getType() + ": " + t.getName()).sorted().toList());
        }
        return response;
    }
    private PlatoIngredienteResponseDto ingredientToResponse(PlatoIngrediente item) {
        PlatoIngredienteResponseDto response = new PlatoIngredienteResponseDto();
        response.setIngredienteId(item.getIngrediente().getId());
        response.setNombre(item.getIngrediente().getNombre());
        response.setCantidad(item.getCantidadTexto());
        response.setDetalle(item.getDetalleIngrediente());
        response.setObligatorio(item.getObligatorio());
        return response;
    }
}
