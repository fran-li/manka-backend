package pe.edu.utec.manka.controller;

import org.springframework.web.bind.annotation.*;
import pe.edu.utec.manka.dto.PlatoResponseDto;
import pe.edu.utec.manka.service.PlatoService;

import java.util.List;

@RestController
@RequestMapping("/dishes")
public class PlatoController {
    private final PlatoService platoService;

    public PlatoController(PlatoService platoService) {
        this.platoService = platoService;
    }

    @GetMapping
    public List<PlatoResponseDto> search(@RequestParam(required = false) String search,
                                         @RequestParam(required = false) Integer maxMinutes) {
        return platoService.search(search, maxMinutes);
    }

    @GetMapping("/page")
    public org.springframework.data.domain.Page<PlatoResponseDto> searchPage(
            @RequestParam(required = false) String search,
            @RequestParam(required = false) Integer maxMinutes,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return platoService.searchPage(search, maxMinutes, page, size);
    }

    @GetMapping("/{id}")
    public PlatoResponseDto getById(@PathVariable Long id) {
        return platoService.getById(id);
    }
}
