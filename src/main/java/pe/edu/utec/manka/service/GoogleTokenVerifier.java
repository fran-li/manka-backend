package pe.edu.utec.manka.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Service;
import pe.edu.utec.manka.exception.BusinessRuleException;
import pe.edu.utec.manka.exception.InvalidCredentialsException;

import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;

/** Verifica firma/expiración con las claves oficiales de Google y comprueba issuer + audience. */
@Service
public class GoogleTokenVerifier {
    // Los certificados de Google rotan; NimbusJwtDecoder los obtiene vía JWKS.
    private static final String GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs";
    private final JwtDecoder googleDecoder;
    private final Set<String> allowedClientIds;

    public GoogleTokenVerifier(@Value("${manka.google.client-ids:}") String clientIds) {
        this.googleDecoder = NimbusJwtDecoder.withJwkSetUri(GOOGLE_JWKS).build();
        this.allowedClientIds = Arrays.stream(clientIds.split(","))
                .map(String::trim)
                .filter(id -> !id.isBlank())
                .collect(Collectors.toUnmodifiableSet());
    }

    public GoogleIdentity verify(String credential) {
        if (allowedClientIds.isEmpty()) {
            throw new BusinessRuleException("Google Sign-In no está configurado en el backend.");
        }
        if (credential == null || credential.isBlank()) {
            throw new InvalidCredentialsException("Falta la credencial de Google.");
        }

        final Jwt jwt;
        try {
            // Verifica firma RSA y tiempos (exp/nbf) usando las claves públicas de Google.
            jwt = googleDecoder.decode(credential);
        } catch (JwtException ex) {
            throw new InvalidCredentialsException("Credencial de Google inválida o expirada.");
        }

        String issuer = jwt.getIssuer() == null ? "" : jwt.getIssuer().toString();
        boolean validIssuer = "accounts.google.com".equals(issuer)
                || "https://accounts.google.com".equals(issuer);
        boolean validAudience = jwt.getAudience() != null
                && jwt.getAudience().stream().anyMatch(allowedClientIds::contains);
        String subject = jwt.getSubject();
        String email = jwt.getClaimAsString("email");
        Boolean verified = jwt.getClaimAsBoolean("email_verified");

        if (!validIssuer || !validAudience || subject == null || subject.isBlank()
                || email == null || email.isBlank() || !Boolean.TRUE.equals(verified)) {
            throw new InvalidCredentialsException("No fue posible verificar la identidad de Google.");
        }

        return new GoogleIdentity(
                subject,
                email.trim().toLowerCase(java.util.Locale.ROOT),
                jwt.getClaimAsString("given_name"),
                jwt.getClaimAsString("family_name")
        );
    }

    public record GoogleIdentity(String subject, String email, String givenName, String familyName) {}
}
