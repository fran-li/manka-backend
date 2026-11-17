package pe.edu.utec.manka.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "dish_ingredient_source_lines", uniqueConstraints = @UniqueConstraint(columnNames = {"dish_id", "line_index"}))
public class IngredienteLineaOriginal {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "dish_id", nullable = false)
    private Long platoId;
    @Column(name = "line_index", nullable = false)
    private Integer posicion;
    @Column(name = "original_text", nullable = false, columnDefinition = "TEXT")
    private String textoOriginal;
    @Column(name = "ingredient_id")
    private Long ingredienteId;

    public Long getId(){return id;}
    public Long getPlatoId(){return platoId;}
    public Integer getPosicion(){return posicion;}
    public String getTextoOriginal(){return textoOriginal;}
    public Long getIngredienteId(){return ingredienteId;}
}
