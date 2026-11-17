package pe.edu.utec.manka.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;
import pe.edu.utec.manka.AbstractContainerBaseTest;
import pe.edu.utec.manka.entity.IngredientAlias;
import pe.edu.utec.manka.entity.Ingrediente;
import pe.edu.utec.manka.repository.IngredientAliasRepository;
import pe.edu.utec.manka.repository.IngredienteRepository;

import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasItem;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class CatalogoMejoradoIntegrationTest extends AbstractContainerBaseTest {
    @Autowired private MockMvc mockMvc;
    @Autowired private IngredienteRepository ingredientes;
    @Autowired private IngredientAliasRepository aliasRepository;

    @Test
    void listadosPaginadosMantienenFormatoNuevo() throws Exception {
        mockMvc.perform(get("/dishes/page?page=0&size=5")
                .with(jwt()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.content.length()").value(5))
            .andExpect(jsonPath("$.totalElements").value(greaterThan(10)));
        mockMvc.perform(get("/ingredients/page?page=0&size=5")
                .with(jwt()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.content.length()").value(5));
    }

    @Test
    @Transactional
    void aliasPermiteBuscarIngredienteCanonico() throws Exception {
        Ingrediente tomate = ingredientes.findByNombreContainingIgnoreCaseOrderByNombreAsc("Tomate")
                .stream().filter(i -> i.getNombre().equalsIgnoreCase("Tomate"))
                .findFirst().orElseThrow();
        IngredientAlias alias = new IngredientAlias();
        alias.setAlias("Jitomate");
        alias.setAliasKey("jitomate");
        alias.setIngrediente(tomate);
        aliasRepository.saveAndFlush(alias);
        mockMvc.perform(get("/ingredients/page?search=jitomate&page=0&size=10")
                .with(jwt()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.content[*].nombre").value(hasItem("Tomate")));
    }
}
