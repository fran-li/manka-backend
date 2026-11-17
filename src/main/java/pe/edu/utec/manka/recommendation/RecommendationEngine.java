package pe.edu.utec.manka.recommendation;

import org.springframework.stereotype.Component;
import pe.edu.utec.manka.entity.Plato;
import pe.edu.utec.manka.entity.PlatoIngrediente;

import java.util.Comparator;
import java.util.List;

@Component
public class RecommendationEngine {
    private final ScorerComposer scorerComposer;

    public RecommendationEngine(ScorerComposer scorerComposer) {
        this.scorerComposer = scorerComposer;
    }

    // Conserva el método antiguo para los consumidores existentes.
    public List<RecommendationResult> rank(List<Plato> candidates, RecommendationContext context, int limit) {
        return rankAll(candidates, context).stream().limit(limit).toList();
    }

    // Evalúa todas las recetas elegibles y conserva el ranking completo.
    public List<RecommendationResult> rankAll(List<Plato> candidates, RecommendationContext context) {
        return candidates.stream()
                .map(plato -> evaluate(plato, context))
                .filter(result -> result.getMatchedIngredients() > 0)
                .sorted(Comparator
                        .comparingDouble((RecommendationResult result) -> result.getScoring().getFinalScore())
                        .reversed()
                        // Desempate determinista, para que una receta no salte entre páginas.
                        .thenComparing(result -> result.getPlato().getId()))
                .toList();
    }

    private RecommendationResult evaluate(Plato plato, RecommendationContext context) {
        List<PlatoIngrediente> required = IngredientMatching.requiredIngredients(plato.getIngredientes());

        int matched = (int) required.stream().filter(pi -> IngredientMatching
                        .hasIngredient(pi.getIngrediente(), context.getAvailableIngredients())).count();

        List<String> missing = required.stream()
                .filter(pi -> !IngredientMatching.hasIngredient(pi.getIngrediente(), context.getAvailableIngredients()))
                .map(pi -> pi.getIngrediente().getNombre())
                .toList();

        ScoringResult scoring = scorerComposer.calculate(plato, context);
        return new RecommendationResult(plato, scoring, matched, required.size(), missing);
    }
}
