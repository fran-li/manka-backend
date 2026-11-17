package pe.edu.utec.manka.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import pe.edu.utec.manka.entity.Plato;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.Set;

public interface PlatoRepository extends JpaRepository<Plato, Long> {
    // Conservado para los tests/consumidores antiguos.
    @Query("""
            select distinct p from Plato p
            left join fetch p.categoriaProteina
            left join fetch p.ingredientes pi
            left join fetch pi.ingrediente i
            left join fetch i.parent
            where p.tiempoPreparacion <= :maxMinutes
            """)
    List<Plato> findCandidates(@Param("maxMinutes") Integer maxMinutes);

    // Filtrar en SQL las recetas que comparten ingredientes ANTES de cargarlas.
    @Query("""
            select distinct p.id from Plato p
            join p.ingredientes pi
            join pi.ingrediente i
            left join i.parent parent
            where p.tiempoPreparacion <= :maxMinutes
              and pi.obligatorio = true
              and (i.id in :availableIds
                   or parent.id in :availableIds
                   or i.id in :parentIds)
            """)
    List<Long> findCandidateIds(@Param("maxMinutes") Integer maxMinutes,
                                @Param("availableIds") Set<Long> availableIds,
                                @Param("parentIds") Set<Long> parentIds);

    @Query("""
            select distinct p from Plato p
            left join fetch p.categoriaProteina
            left join fetch p.proteinSources
            left join fetch p.ingredientes pi
            left join fetch pi.ingrediente i
            left join fetch i.parent
            where p.id in :ids
            """)
    List<Plato> findDetailedByIds(@Param("ids") Collection<Long> ids);

    @Override
    @EntityGraph(attributePaths = {"categoriaProteina", "ingredientes", "ingredientes.ingrediente", "ingredientes.ingrediente.parent"})
    Optional<Plato> findById(Long id);

    // Consultas derivadas: no utilizan parámetros opcionales nulos en JPQL.
    Page<Plato> findByNombreContainingIgnoreCase(String nombre, Pageable pageable);

    Page<Plato> findByTiempoPreparacionLessThanEqual(Integer maxMinutes, Pageable pageable);

    Page<Plato> findByNombreContainingIgnoreCaseAndTiempoPreparacionLessThanEqual(
            String nombre, Integer maxMinutes, Pageable pageable);

    @EntityGraph(attributePaths = {"categoriaProteina"})
    List<Plato> findByNombreContainingIgnoreCaseOrderByNombreAsc(String nombre);
}
