package pe.edu.utec.manka.entity;
import jakarta.persistence.*;
@Entity @Table(name="tags", uniqueConstraints = @UniqueConstraint(columnNames = {"name", "type"}))
public class DishTag {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(nullable = false, length = 120) private String name;
    @Column(nullable = false, length = 30) private String type;
    public Long getId(){return id;} public void setId(Long id){this.id=id;}
    public String getName(){return name;} public void setName(String name){this.name=name;}
    public String getType(){return type;} public void setType(String type){this.type=type;}
}
