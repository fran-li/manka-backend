package pe.edu.utec.manka.service;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pe.edu.utec.manka.dto.LoginRequestDto;
import pe.edu.utec.manka.dto.LoginResponseDto;
import pe.edu.utec.manka.entity.Rol;
import pe.edu.utec.manka.entity.TipoRol;
import pe.edu.utec.manka.entity.Usuario;
import pe.edu.utec.manka.event.UserRegisteredEvent;
import pe.edu.utec.manka.exception.ConflictException;
import pe.edu.utec.manka.exception.InvalidCredentialsException;
import pe.edu.utec.manka.exception.RoleNotFoundException;
import pe.edu.utec.manka.repository.RolRepository;
import pe.edu.utec.manka.repository.UsuarioRepository;

import java.util.Locale;
import java.util.UUID;

@Service
public class AuthService {
    private final UsuarioRepository usuarioRepository;
    private final RolRepository rolRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final RefreshTokenService refreshTokenService;
    private final GoogleTokenVerifier googleTokenVerifier;
    private final ApplicationEventPublisher eventPublisher;

    public AuthService(UsuarioRepository usuarioRepository, RolRepository rolRepository,
                       PasswordEncoder passwordEncoder, JwtService jwtService,
                       RefreshTokenService refreshTokenService,
                       GoogleTokenVerifier googleTokenVerifier,
                       ApplicationEventPublisher eventPublisher) {
        this.usuarioRepository = usuarioRepository;
        this.rolRepository = rolRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.refreshTokenService = refreshTokenService;
        this.googleTokenVerifier = googleTokenVerifier;
        this.eventPublisher = eventPublisher;
    }

    @Transactional
    public LoginResponseDto login(LoginRequestDto request) {
        String email = request.getEmail().trim().toLowerCase(Locale.ROOT);
        Usuario user = usuarioRepository.findByEmail(email)
                .orElseThrow(() -> new InvalidCredentialsException("Invalid email or password"));
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new InvalidCredentialsException("Invalid email or password");
        }
        return issueTokens(user);
    }

    /** Registrar/iniciar sesión con el ID token de Google y emitir JWT de Manka. */
    @Transactional
    public LoginResponseDto loginWithGoogle(String credential) {
        GoogleTokenVerifier.GoogleIdentity identity = googleTokenVerifier.verify(credential);

        // sub es el identificador estable de Google, no el correo electrónico.
        Usuario user = usuarioRepository.findByGoogleSubject(identity.subject())
                .orElseGet(() -> createGoogleUser(identity));
        return issueTokens(user);
    }

    private Usuario createGoogleUser(GoogleTokenVerifier.GoogleIdentity identity) {
        // No vincular por coincidencia de correo: podría apropiarse de una cuenta preexistente.
        if (usuarioRepository.existsByEmail(identity.email())) {
            throw new ConflictException("Ya existe una cuenta con ese correo. "
                    + "Inicia sesión con tu contraseña; la vinculación con Google aún no está habilitada.");
        }
        Rol userRole = rolRepository.findByName(TipoRol.USER)
                .orElseThrow(() -> new RoleNotFoundException("USER role not found"));

        Usuario user = new Usuario();
        user.setFirstName(nonBlank(identity.givenName(), "Usuario"));
        user.setLastName(nonBlank(identity.familyName(), "Google"));
        user.setEmail(identity.email());
        user.setGoogleSubject(identity.subject());
        // La columna password es NOT NULL: hash aleatorio e imposible de usar como login local.
        user.setPassword(passwordEncoder.encode(UUID.randomUUID().toString()));
        user.getRoles().add(userRole); // Jamás se concede ADMIN por autenticarse con Google.

        Usuario saved = usuarioRepository.saveAndFlush(user);
        eventPublisher.publishEvent(new UserRegisteredEvent(
                this, saved.getId(), saved.getEmail(), saved.getFirstName()));
        return saved;
    }

    private String nonBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    @Transactional
    public LoginResponseDto refresh(String refreshToken) {
        Usuario user = refreshTokenService.consume(refreshToken);
        return issueTokens(user);
    }

    @Transactional
    public void logout(String refreshToken) {
        refreshTokenService.revoke(refreshToken);
    }

    private LoginResponseDto issueTokens(Usuario user) {
        String accessToken = jwtService.generateAccessToken(user);
        String refreshToken = refreshTokenService.create(user);
        return new LoginResponseDto(accessToken, refreshToken);
    }
}
