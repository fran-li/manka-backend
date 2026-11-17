package pe.edu.utec.manka.controller;

import org.springframework.web.bind.annotation.*;
import pe.edu.utec.manka.dto.IngredienteResponseDto;
import pe.edu.utec.manka.service.IngredienteService;

import java.util.List;

@RestController
@RequestMapping("/ingredients")
public class IngredienteController {
    private final IngredienteService ingredienteService;

    public IngredienteController(IngredienteService ingredienteService) {
        this.ingredienteService = ingredienteService;
    }

    @GetMapping
    public List<IngredienteResponseDto> search(@RequestParam(required = false) String search) {
        return ingredienteService.search(search);
    }
    @GetMapping("/page")
    public org.springframework.data.domain.Page<IngredienteResponseDto> searchPage(
            @RequestParam(required = false) String search,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ingredienteService.searchPage(search, page, size);
    }
}
