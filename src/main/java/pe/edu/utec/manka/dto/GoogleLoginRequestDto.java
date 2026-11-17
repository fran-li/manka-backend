package pe.edu.utec.manka.dto;

import jakarta.validation.constraints.NotBlank;

// CredentialResponse.credential del botón oficial de Google Identity Services.
public record GoogleLoginRequestDto(@NotBlank String credential) {}
