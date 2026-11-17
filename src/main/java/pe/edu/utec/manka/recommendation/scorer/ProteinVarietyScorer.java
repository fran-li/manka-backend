package pe.edu.utec.manka.recommendation.scorer;

import org.springframework.stereotype.Component;
import pe.edu.utec.manka.entity.CategoriaProteina;
import pe.edu.utec.manka.entity.HistorialCocina;
import pe.edu.utec.manka.entity.Plato;
import pe.edu.utec.manka.entity.ProteinSource;
import java.util.Set;
import java.util.stream.Collectors;
import pe.edu.utec.manka.recommendation.RecommendationContext;
import pe.edu.utec.manka.recommendation.Scorer;

import java.time.LocalDateTime;

@Component
public class ProteinVarietyScorer implements Scorer {
    @Override
    public String getName() { return "proteinVariety"; }

    @Override
    public double score(Plato plato, RecommendationContext context) {
        Set<Long> sources = plato.getProteinSources().stream()
                .map(ProteinSource::getId).collect(Collectors.toSet());

        // "Otros" o fuente desconocida no es una proteína concreta y no debe
        // penalizar indiscriminadamente a miles de recetas distintas.
        if (sources.isEmpty()) {
            CategoriaProteina category = plato.getCategoriaProteina();
            if (category == null || "Otros".equalsIgnoreCase(category.getNombre())) return 100.0;
            return scoreLegacy(category, context);
        }
        LocalDateTime sevenDaysAgo = LocalDateTime.now().minusDays(7);
        long overlaps = context.getRecentHistory().stream()
                .filter(h -> h.getCocinadoEn().isAfter(sevenDaysAgo))
                .map(HistorialCocina::getPlato)
                .filter(p -> p.getProteinSources().stream()
                        .map(ProteinSource::getId).anyMatch(sources::contains))
                .count();
        if (overlaps == 0) return 100.0;
        if (overlaps == 1) return 70.0;
        return 30.0;
    }

    private double scoreLegacy(CategoriaProteina category, RecommendationContext context) {
        LocalDateTime sevenDaysAgo = LocalDateTime.now().minusDays(7);
        long repeats = context.getRecentHistory().stream()
                .filter(h -> h.getCocinadoEn().isAfter(sevenDaysAgo))
                .map(HistorialCocina::getPlato)
                .filter(p -> p.getCategoriaProteina() != null)
                .filter(p -> p.getCategoriaProteina().getId().equals(category.getId()))
                .count();
        return repeats == 0 ? 100.0 : repeats == 1 ? 70.0 : 30.0;
    }
}
