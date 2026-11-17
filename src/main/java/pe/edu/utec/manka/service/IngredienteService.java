package pe.edu.utec.manka.service;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pe.edu.utec.manka.dto.IngredienteResponseDto;
import pe.edu.utec.manka.entity.Ingrediente;
import pe.edu.utec.manka.repository.IngredienteRepository;
import java.text.Normalizer;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

@Service
public class IngredienteService {
    private final IngredienteRepository ingredienteRepository;
    public IngredienteService(IngredienteRepository ingredienteRepository) {
        this.ingredienteRepository = ingredienteRepository;
    }

    @Transactional(readOnly = true)
    public List<IngredienteResponseDto> search(String search) {
        if (search == null || search.isBlank())
            return ingredienteRepository.findBySeleccionableTrueOrderByNombreAsc().stream().map(this::toResponse).toList();
        String term = search.trim().toLowerCase(Locale.ROOT);
        Optional<Ingrediente> exact = ingredienteRepository.findByNombreIgnoreCaseAndSeleccionableTrue(term);
        if (exact.isPresent()) return List.of(toResponse(exact.get()));
        Optional<Ingrediente> exactAlias = ingredienteRepository.findByAliasKey(key(term));
        if (exactAlias.isPresent()) return List.of(toResponse(exactAlias.get()));
        return ingredienteRepository.findAllWithAliases(term,key(term)).stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public Page<IngredienteResponseDto> searchPage(String search,int page,int size) {
        if(page<0 || size<1 || size>100) throw new IllegalArgumentException("page >= 0 y size 1..100");
        PageRequest paging = PageRequest.of(page,size);
        if(search==null || search.isBlank()) {
            return ingredienteRepository.findBySeleccionableTrue(
                PageRequest.of(page,size,Sort.by("nombre").ascending())).map(this::toResponse);
        }
        String term = search.trim().toLowerCase(Locale.ROOT);
        Optional<Ingrediente> exact = ingredienteRepository.findByNombreIgnoreCaseAndSeleccionableTrue(term);
        if(exact.isPresent()) {
            List<IngredienteResponseDto> content = page==0 ? List.of(toResponse(exact.get())) : List.of();
            return new PageImpl<>(content,paging,1L);
        }
        Optional<Ingrediente> exactAlias = ingredienteRepository.findByAliasKey(key(term));
        if (exactAlias.isPresent()) {
            List<IngredienteResponseDto> content = page==0 ? List.of(toResponse(exactAlias.get())) : List.of();
            return new PageImpl<>(content,paging,1L);
        }
        return ingredienteRepository.searchWithAliases(term,key(term),paging).map(this::toResponse);
    }

    private static String key(String text) {
        if(text==null) return "";
        String decomposed = Normalizer.normalize(text.toLowerCase(Locale.ROOT),Normalizer.Form.NFD);
        return decomposed.replaceAll("\\p{M}+", "").replaceAll("[^a-z0-9 ]+", " ").replaceAll("\\s+", " ").trim();
    }

    public IngredienteResponseDto toResponse(Ingrediente ingredient) {
        IngredienteResponseDto response = new IngredienteResponseDto();
        response.setId(ingredient.getId()); response.setNombre(ingredient.getNombre());
        if(ingredient.getParent()!=null) {
            response.setParentId(ingredient.getParent().getId());
            response.setParentNombre(ingredient.getParent().getNombre());
        }
        return response;
    }
}
