package pe.edu.utec.manka.entity;

import jakarta.persistence.*;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "dishes", indexes = { @Index(name = "idx_dishes_time", columnList = "preparation_minutes"), @Index(name = "idx_dishes_name", columnList = "name") })
public class Plato {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "name", nullable = false, length = 255)
    private String nombre;

    // Identificador del dataset, distinto al ID interno de PostgreSQL.
    @Column(name = "source_id", unique = true)
    private Long sourceId;

    @Column(name = "source_url", length = 1000)
    private String sourceUrl;

    @Column(name = "source_ingredients_text", columnDefinition = "TEXT")
    private String ingredientesOriginales;

    @Column(name = "country", length = 100)
    private String country;

    @Column(name = "servings")
    private Integer servings;

    @Column(name = "meal_type", length = 120)
    private String mealType;

    @Column(name = "rating_average")
    private Double ratingAverage;

    @Column(name = "rating_votes")
    private Integer ratingVotes;

    @Column(name = "duration_estimated", nullable = false)
    private Boolean durationEstimated = false;

    @Column(name = "difficulty_estimated", nullable = false)
    private Boolean difficultyEstimated = false;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(name = "dish_protein_sources",
            joinColumns = @JoinColumn(name = "dish_id"),
            inverseJoinColumns = @JoinColumn(name = "protein_source_id"))
    private java.util.Set<ProteinSource> proteinSources = new java.util.HashSet<>();

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(name = "dish_tags",
            joinColumns = @JoinColumn(name = "dish_id"),
            inverseJoinColumns = @JoinColumn(name = "tag_id"))
    private java.util.Set<DishTag> tags = new java.util.HashSet<>();

    @Column(name = "preparation_minutes")
    private Integer tiempoPreparacion;

    @Enumerated(EnumType.STRING)
    @Column(name = "difficulty")
    private Dificultad dificultad;

    @Column(name = "popularity_score", nullable = false)
    private Integer popularidad;

    @Column(name = "preparation", columnDefinition = "TEXT", nullable = false)
    private String preparacion;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "protein_category_id")
    private CategoriaProteina categoriaProteina;

    @OneToMany(mappedBy = "plato", fetch = FetchType.LAZY)
    private List<PlatoIngrediente> ingredientes = new ArrayList<>();

    public Long getSourceId() { return sourceId; }
    public void setSourceId(Long sourceId) { this.sourceId = sourceId; }
    public String getIngredientesOriginales() { return ingredientesOriginales; }
    public void setIngredientesOriginales(String ingredientesOriginales) { this.ingredientesOriginales = ingredientesOriginales; }
    public String getSourceUrl() { return sourceUrl; }
    public void setSourceUrl(String sourceUrl) { this.sourceUrl = sourceUrl; }
    public String getCountry() { return country; }
    public void setCountry(String country) { this.country = country; }
    public Integer getServings() { return servings; }
    public void setServings(Integer servings) { this.servings = servings; }
    public String getMealType() { return mealType; }
    public void setMealType(String mealType) { this.mealType = mealType; }
    public Double getRatingAverage() { return ratingAverage; }
    public void setRatingAverage(Double ratingAverage) { this.ratingAverage = ratingAverage; }
    public Integer getRatingVotes() { return ratingVotes; }
    public void setRatingVotes(Integer ratingVotes) { this.ratingVotes = ratingVotes; }
    public Boolean getDurationEstimated() { return durationEstimated; }
    public void setDurationEstimated(Boolean durationEstimated) { this.durationEstimated = durationEstimated; }
    public Boolean getDifficultyEstimated() { return difficultyEstimated; }
    public void setDifficultyEstimated(Boolean difficultyEstimated) { this.difficultyEstimated = difficultyEstimated; }
    public java.util.Set<ProteinSource> getProteinSources() { return proteinSources; }
    public void setProteinSources(java.util.Set<ProteinSource> proteinSources) { this.proteinSources = proteinSources; }
    public java.util.Set<DishTag> getTags() { return tags; }
    public void setTags(java.util.Set<DishTag> tags) { this.tags = tags; }
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getNombre() { return nombre; }
    public void setNombre(String nombre) { this.nombre = nombre; }
    public Integer getTiempoPreparacion() { return tiempoPreparacion; }
    public void setTiempoPreparacion(Integer tiempoPreparacion) { this.tiempoPreparacion = tiempoPreparacion; }
    public Dificultad getDificultad() { return dificultad; }
    public void setDificultad(Dificultad dificultad) { this.dificultad = dificultad; }
    public Integer getPopularidad() { return popularidad; }
    public void setPopularidad(Integer popularidad) { this.popularidad = popularidad; }
    public String getPreparacion() { return preparacion; }
    public void setPreparacion(String preparacion) { this.preparacion = preparacion; }
    public CategoriaProteina getCategoriaProteina() { return categoriaProteina; }
    public void setCategoriaProteina(CategoriaProteina categoriaProteina) { this.categoriaProteina = categoriaProteina; }
    public List<PlatoIngrediente> getIngredientes() { return ingredientes; }
    public void setIngredientes(List<PlatoIngrediente> ingredientes) { this.ingredientes = ingredientes; }
}
