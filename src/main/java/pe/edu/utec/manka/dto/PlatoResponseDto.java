package pe.edu.utec.manka.dto;

import pe.edu.utec.manka.entity.Dificultad;
import java.util.List;

public class PlatoResponseDto {
    private Long id;
    private Long sourceId;
    private String sourceUrl;
    private String country;
    private Integer servings;
    private String mealType;
    private Double ratingAverage;
    private Integer ratingVotes;
    private Boolean durationEstimated;
    private Boolean difficultyEstimated;
    private List<String> proteinSources;
    private List<String> tags;

    private String nombre;
    private Integer tiempoPreparacion;
    private Dificultad dificultad;
    private Integer popularidad;
    private String categoriaProteina;
    private String preparacion;
    private List<PlatoIngredienteResponseDto> ingredientes;
    private List<String> ingredientesCsv;
    public List<String> getIngredientesCsv() { return ingredientesCsv; }
    public void setIngredientesCsv(List<String> value) { this.ingredientesCsv=value; }

    public Long getSourceId(){return sourceId;} public void setSourceId(Long x){sourceId=x;}
    public String getSourceUrl(){return sourceUrl;} public void setSourceUrl(String x){sourceUrl=x;}
    public String getCountry(){return country;} public void setCountry(String x){country=x;}
    public Integer getServings(){return servings;} public void setServings(Integer x){servings=x;}
    public String getMealType(){return mealType;} public void setMealType(String x){mealType=x;}
    public Double getRatingAverage(){return ratingAverage;} public void setRatingAverage(Double x){ratingAverage=x;}
    public Integer getRatingVotes(){return ratingVotes;} public void setRatingVotes(Integer x){ratingVotes=x;}
    public Boolean getDurationEstimated(){return durationEstimated;} public void setDurationEstimated(Boolean x){durationEstimated=x;}
    public Boolean getDifficultyEstimated(){return difficultyEstimated;} public void setDifficultyEstimated(Boolean x){difficultyEstimated=x;}
    public List<String> getProteinSources(){return proteinSources;} public void setProteinSources(List<String> x){proteinSources=x;}
    public List<String> getTags(){return tags;} public void setTags(List<String> x){tags=x;}
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
    public String getCategoriaProteina() { return categoriaProteina; }
    public void setCategoriaProteina(String categoriaProteina) { this.categoriaProteina = categoriaProteina; }
    public String getPreparacion() { return preparacion; }
    public void setPreparacion(String preparacion) { this.preparacion = preparacion; }
    public List<PlatoIngredienteResponseDto> getIngredientes() { return ingredientes; }
    public void setIngredientes(List<PlatoIngredienteResponseDto> ingredientes) { this.ingredientes = ingredientes; }
}
