package pe.edu.utec.manka.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import pe.edu.utec.manka.entity.IngredienteLineaOriginal;
import java.util.Collection;
import java.util.List;

public interface IngredienteLineaOriginalRepository extends JpaRepository<IngredienteLineaOriginal, Long> {
    List<IngredienteLineaOriginal> findByPlatoIdOrderByPosicionAsc(Long platoId);
    List<IngredienteLineaOriginal> findByPlatoIdAndIngredienteIdInOrderByPosicionAsc(
            Long platoId, Collection<Long> ingredienteIds);
}
