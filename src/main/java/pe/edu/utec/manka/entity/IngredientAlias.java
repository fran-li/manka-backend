package pe.edu.utec.manka.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "ingredient_aliases", uniqueConstraints = @UniqueConstraint(columnNames = "alias_key"))
public class IngredientAlias {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "alias", nullable = false, length = 255)
    private String alias;
    @Column(name = "alias_key", nullable = false, length = 255, unique = true)
    private String aliasKey;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "ingredient_id", nullable = false)
    private Ingrediente ingrediente;
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getAlias() { return alias; }
    public void setAlias(String alias) { this.alias = alias; }
    public String getAliasKey() { return aliasKey; }
    public void setAliasKey(String aliasKey) { this.aliasKey = aliasKey; }
    public Ingrediente getIngrediente() { return ingrediente; }
    public void setIngrediente(Ingrediente ingrediente) { this.ingrediente = ingrediente; }
}
