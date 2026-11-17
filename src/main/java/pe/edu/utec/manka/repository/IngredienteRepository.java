package pe.edu.utec.manka.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import pe.edu.utec.manka.entity.Ingrediente;
import java.util.List;
import java.util.Optional;

public interface IngredienteRepository extends JpaRepository<Ingrediente, Long> {
    List<Ingrediente> findByNombreContainingIgnoreCaseOrderByNombreAsc(String nombre);
    Optional<Ingrediente> findByNombreIgnoreCaseAndSeleccionableTrue(String nombre);
    Page<Ingrediente> findBySeleccionableTrue(Pageable pageable);
    @Query("select a.ingrediente from IngredientAlias a where a.aliasKey = :key and a.ingrediente.seleccionable = true")
    Optional<Ingrediente> findByAliasKey(@Param("key") String key);
    List<Ingrediente> findBySeleccionableTrueOrderByNombreAsc();

    @Query(value = """
        select i from Ingrediente i
        where i.seleccionable = true and (
           lower(i.nombre) like concat('%', :term, '%')
           or exists (select 1 from IngredientAlias a
                      where a.ingrediente = i
                        and (lower(a.alias) like concat('%', :term, '%') or a.aliasKey = :key))
        )
        order by case
          when lower(i.nombre) = :term then 0
          when lower(i.nombre) like concat(:term, '%') then 1
          when lower(i.nombre) like concat('%', :term, '%') then 2
          else 3 end, i.nombre asc
        """,
        countQuery = """
        select count(i) from Ingrediente i
        where i.seleccionable = true and (
           lower(i.nombre) like concat('%', :term, '%')
           or exists (select 1 from IngredientAlias a
                      where a.ingrediente = i
                        and (lower(a.alias) like concat('%', :term, '%') or a.aliasKey = :key))
        )
        """)
    Page<Ingrediente> searchWithAliases(@Param("term") String term,
                                        @Param("key") String key,
                                        Pageable pageable);

    @Query("""
        select i from Ingrediente i
        where i.seleccionable = true and (
            lower(i.nombre) like concat('%', :term, '%')
            or exists (
                select 1 from IngredientAlias a
                where a.ingrediente = i
                  and (
                      lower(a.alias) like concat('%', :term, '%')
                      or a.aliasKey = :key
                  )
            )
        )
        order by
            case
                when lower(i.nombre) = :term then 0
                else 1
            end,
            i.nombre asc
        """)
    List<Ingrediente> findAllWithAliases(@Param("term") String term,
                                        @Param("key") String key);
}
