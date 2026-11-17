package pe.edu.utec.manka.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import pe.edu.utec.manka.entity.RefreshToken;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.Optional;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {
    Optional<RefreshToken> findByTokenHash(String tokenHash);

    @Modifying
    @Query("DELETE FROM RefreshToken t WHERE t.usuario.id = :userId")
    int deleteByUserId(@Param("userId") Long userId);
}
