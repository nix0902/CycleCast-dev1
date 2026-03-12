# SECURITY

> **Версия:** 3.2 Final | **CycleCast Security Architecture**

---

## 1. АРХИТЕКТУРА БЕЗОПАСНОСТИ

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    CLIENTS                                        │
│                    Web App │ Mobile │ External API Clients                       │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   API GATEWAY                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ HTTPS/TLS   │  │ Rate Limit  │  │ Auth Check  │  │ Input Validation    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘    │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   Go Backend     │       │ Python Quant     │       │  HashiCorp Vault │
│                  │       │                  │       │                  │
│ - JWT Validation │       │ - mTLS           │       │ - API Keys       │
│ - RBAC           │       │ - Service Token  │       │ - DB Credentials │
│ - Audit Log      │       │                  │       │ - JWT Secrets    │
└────────┬─────────┘       └──────────────────┘       └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                     DATA LAYER                                    │
│   PostgreSQL (encrypted at rest) │ Redis (TLS) │ TimescaleDB                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. АУТЕНТИФИКАЦИЯ

### 2.1 JWT Tokens

#### Структура Token

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-id-123"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "role": "analyst",
    "permissions": ["read:signals", "read:analysis"],
    "iat": 1704110400,
    "exp": 1704196800,
    "iss": "cyclecast",
    "aud": "cyclecast-api"
  }
}
```

#### Token Lifecycle

```go
// Генерация
func GenerateToken(user *User) (string, error) {
    claims := jwt.MapClaims{
        "sub":         user.ID,
        "email":       user.Email,
        "role":        user.Role,
        "permissions": user.Permissions,
        "iat":         time.Now().Unix(),
        "exp":         time.Now().Add(24 * time.Hour).Unix(),
        "iss":         "cyclecast",
        "aud":         "cyclecast-api",
    }
    
    token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
    token.Header["kid"] = keyID
    
    return token.SignedString(privateKey)
}

// Валидация
func ValidateToken(tokenString string) (*Claims, error) {
    token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
        // Verify signing method
        if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
        }
        
        // Get key by kid
        kid := token.Header["kid"].(string)
        return getPublicKey(kid)
    })
    
    if err != nil {
        return nil, err
    }
    
    claims, ok := token.Claims.(jwt.MapClaims)
    if !ok || !token.Valid {
        return nil, ErrInvalidToken
    }
    
    // Validate claims
    if err := validateClaims(claims); err != nil {
        return nil, err
    }
    
    return mapClaimsToStruct(claims), nil
}
```

#### Refresh Token

```go
type RefreshToken struct {
    ID        uuid.UUID `json:"id"`
    UserID    uuid.UUID `json:"user_id"`
    Token     string    `json:"-"`
    ExpiresAt time.Time `json:"expires_at"`
    Revoked   bool      `json:"revoked"`
}

// Rotation при refresh
func RefreshAccessToken(refreshToken string) (*TokenPair, error) {
    // Validate refresh token
    stored, err := repo.GetRefreshToken(refreshToken)
    if err != nil || stored.Revoked || stored.ExpiresAt.Before(time.Now()) {
        return nil, ErrInvalidRefreshToken
    }
    
    // Revoke old token (rotation)
    repo.RevokeRefreshToken(stored.ID)
    
    // Generate new pair
    user, _ := repo.GetUser(stored.UserID)
    return GenerateTokenPair(user)
}
```

### 2.2 API Keys

#### Структура

```go
type APIKey struct {
    ID          uuid.UUID `json:"id"`
    UserID      uuid.UUID `json:"user_id"`
    Name        string    `json:"name"`
    Key         string    `json:"-"`        // Хранится как hash
    KeyPrefix   string    `json:"key_prefix"` // cc_live_abc...
    Permissions []string  `json:"permissions"`
    RateLimit   int       `json:"rate_limit"`
    ExpiresAt   *time.Time `json:"expires_at,omitempty"`
    LastUsedAt  *time.Time `json:"last_used_at,omitempty"`
    CreatedAt   time.Time `json:"created_at"`
}
```

#### Генерация

```go
func GenerateAPIKey(userID uuid.UUID, name string, permissions []string) (*APIKey, string, error) {
    // Generate random key
    keyBytes := make([]byte, 32)
    if _, err := rand.Read(keyBytes); err != nil {
        return nil, "", err
    }
    
    key := base64.URLEncoding.EncodeToString(keyBytes)
    prefix := "cc_live_" + key[:8]
    
    apiKey := &APIKey{
        ID:          uuid.New(),
        UserID:      userID,
        Name:        name,
        Key:         hashSHA256(key),
        KeyPrefix:   prefix,
        Permissions: permissions,
        RateLimit:   100, // requests per minute
    }
    
    return apiKey, prefix + key[8:], nil
}

// Валидация
func ValidateAPIKey(key string) (*APIKey, error) {
    if !strings.HasPrefix(key, "cc_live_") {
        return nil, ErrInvalidAPIKey
    }
    
    hashed := hashSHA256(key)
    return repo.FindAPIKeyByHash(hashed)
}
```

---

## 3. АВТОРИЗАЦИЯ (RBAC)

### 3.1 Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | Administrator | `*` (all) |
| `analyst` | Financial Analyst | `read:*`, `write:signals`, `run:backtest` |
| `trader` | Trader | `read:signals`, `read:analysis` |
| `viewer` | Read-only | `read:signals` |

### 3.2 Permissions

```go
const (
    // Market Data
    PermissionReadMarketData   = "read:market_data"
    PermissionWriteMarketData  = "write:market_data"
    
    // Analysis
    PermissionReadAnalysis     = "read:analysis"
    PermissionRunBacktest      = "run:backtest"
    
    // Signals
    PermissionReadSignals      = "read:signals"
    PermissionWriteSignals     = "write:signals"
    
    // Admin
    PermissionManageUsers      = "manage:users"
    PermissionManageAPIKeys    = "manage:api_keys"
    PermissionViewAuditLog     = "view:audit_log"
)

var rolePermissions = map[string][]string{
    "admin": {
        "*", // All permissions
    },
    "analyst": {
        PermissionReadMarketData,
        PermissionWriteMarketData,
        PermissionReadAnalysis,
        PermissionRunBacktest,
        PermissionReadSignals,
        PermissionWriteSignals,
    },
    "trader": {
        PermissionReadSignals,
        PermissionReadAnalysis,
    },
    "viewer": {
        PermissionReadSignals,
    },
}
```

### 3.3 Middleware

```go
func AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Get token from header
        authHeader := r.Header.Get("Authorization")
        if authHeader == "" {
            writeError(w, ErrUnauthorized)
            return
        }
        
        // Bearer or API Key
        var claims *Claims
        var err error
        
        if strings.HasPrefix(authHeader, "Bearer ") {
            token := strings.TrimPrefix(authHeader, "Bearer ")
            claims, err = ValidateToken(token)
        } else if strings.HasPrefix(authHeader, "ApiKey ") {
            key := strings.TrimPrefix(authHeader, "ApiKey ")
            claims, err = ValidateAPIKeyAndGetClaims(key)
        } else {
            writeError(w, ErrInvalidAuthHeader)
            return
        }
        
        if err != nil {
            writeError(w, ErrUnauthorized)
            return
        }
        
        // Add claims to context
        ctx := context.WithValue(r.Context(), ClaimsKey, claims)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func RequirePermission(permission string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            claims := GetClaims(r.Context())
            
            if !claims.HasPermission(permission) {
                writeError(w, ErrForbidden)
                return
            }
            
            next.ServeHTTP(w, r)
        })
    }
}

// Usage
router.Handle("/api/v1/backtest/run",
    AuthMiddleware(
        RequirePermission(PermissionRunBacktest)(
            backtestHandler.Run,
        ),
    ),
)
```

---

## 4. HASHICORP VAULT

### 4.1 Secrets Storage

```hcl
# Vault policy for CycleCast
path "secret/data/cyclecast/*" {
  capabilities = ["read", "list"]
}

path "secret/data/cyclecast/database" {
  capabilities = ["read"]
}

path "secret/data/cyclecast/api-keys" {
  capabilities = ["read", "update"]
}
```

### 4.2 Secrets Structure

```json
// secret/data/cyclecast/database
{
  "data": {
    "host": "localhost",
    "port": 5432,
    "database": "cyclecast",
    "username": "cyclecast_app",
    "password": "super-secret-password"
  }
}

// secret/data/cyclecast/jwt
{
  "data": {
    "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
    "public_key": "-----BEGIN PUBLIC KEY-----...",
    "key_id": "key-2024-01"
  }
}

// secret/data/cyclecast/api-keys/external
{
  "data": {
    "alphavantage": "AV_API_KEY",
    "polygon": "POLYGON_API_KEY",
    "coingecko": "CG_API_KEY"
  }
}
```

### 4.3 Go Vault Client

```go
package vault

import (
    "github.com/hashicorp/vault/api"
)

type VaultClient struct {
    client *api.Client
}

func NewClient(addr, token string) (*VaultClient, error) {
    config := api.DefaultConfig()
    config.Address = addr
    
    client, err := api.NewClient(config)
    if err != nil {
        return nil, err
    }
    
    client.SetToken(token)
    return &VaultClient{client: client}, nil
}

func (v *VaultClient) GetSecret(path string) (map[string]interface{}, error) {
    secret, err := v.client.Logical().Read(path)
    if err != nil {
        return nil, err
    }
    
    if secret == nil {
        return nil, ErrSecretNotFound
    }
    
    return secret.Data["data"].(map[string]interface{}), nil
}

func (v *VaultClient) GetDatabaseCredentials() (*DatabaseCredentials, error) {
    data, err := v.GetSecret("secret/data/cyclecast/database")
    if err != nil {
        return nil, err
    }
    
    return &DatabaseCredentials{
        Host:     data["host"].(string),
        Port:     int(data["port"].(float64)),
        Database: data["database"].(string),
        Username: data["username"].(string),
        Password: data["password"].(string),
    }, nil
}
```

### 4.4 Dynamic Secrets (Database)

```hcl
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL
vault write database/config/cyclecast \
    plugin_name=postgresql-database-plugin \
    allowed_roles="cyclecast-app" \
    connection_url="postgresql://{{username}}:{{password}}@localhost:5432/cyclecast?sslmode=disable" \
    username="postgres" \
    password="admin-password"

# Create role with TTL
vault write database/roles/cyclecast-app \
    db_name=cyclecast \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"
```

---

## 5. TLS/SSL

### 5.1 Configuration

```go
func NewTLSServer(handler http.Handler, certFile, keyFile string) (*http.Server, error) {
    cfg := &tls.Config{
        MinVersion: tls.VersionTLS12,
        CipherSuites: []uint16{
            tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
            tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
        },
        PreferServerCipherSuites: true,
        CurvePreferences:         []tls.CurveID{tls.X25519, tls.CurveP256},
    }
    
    return &http.Server{
        Addr:         ":443",
        Handler:      handler,
        TLSConfig:    cfg,
        TLSNextProto: make(map[string]func(*http.Server, *tls.Conn, http.Handler)),
    }, nil
}
```

### 5.2 mTLS for Python Service

```go
// Go client
func NewGRPCClient(addr string, tlsConfig *tls.Config) (pb.QuantServiceClient, error) {
    creds := credentials.NewTLS(tlsConfig)
    
    conn, err := grpc.Dial(addr, grpc.WithTransportCredentials(creds))
    if err != nil {
        return nil, err
    }
    
    return pb.NewQuantServiceClient(conn), nil
}
```

```python
# Python server
def create_grpc_server(cert_path: str, key_path: str, ca_path: str):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    credentials = grpc.ssl_server_credentials(
        [(key_path, cert_path)],
        root_certificates=open(ca_path, 'rb').read(),
        require_client_auth=True
    )
    
    server.add_secure_port('[::]:50051', credentials)
    return server
```

---

## 6. RATE LIMITING

### 6.1 Token Bucket

```go
type RateLimiter struct {
    tokens      int
    capacity    int
    refillRate  int // tokens per second
    mu          sync.Mutex
    lastRefill  time.Time
}

func (rl *RateLimiter) Allow() bool {
    rl.mu.Lock()
    defer rl.mu.Unlock()
    
    // Refill tokens
    now := time.Now()
    elapsed := now.Sub(rl.lastRefill).Seconds()
    rl.tokens = int(math.Min(float64(rl.capacity), float64(rl.tokens) + elapsed*float64(rl.refillRate)))
    rl.lastRefill = now
    
    if rl.tokens > 0 {
        rl.tokens--
        return true
    }
    
    return false
}
```

### 6.2 Redis-Based

```go
type RedisRateLimiter struct {
    client *redis.Client
    limit  int
    window time.Duration
}

func (r *RedisRateLimiter) Allow(key string) (bool, error) {
    ctx := context.Background()
    now := time.Now().UnixNano()
    windowStart := now - int64(r.window)
    
    pipe := r.client.Pipeline()
    
    // Remove old entries
    pipe.ZRemRangeByScore(ctx, key, "0", fmt.Sprintf("%d", windowStart))
    
    // Count current
    countCmd := pipe.ZCard(ctx, key)
    
    // Add new
    pipe.ZAdd(ctx, key, redis.Z{Score: float64(now), Member: now})
    pipe.Expire(ctx, key, r.window)
    
    _, err := pipe.Exec(ctx)
    if err != nil {
        return false, err
    }
    
    return countCmd.Val() < int64(r.limit), nil
}
```

---

## 7. INPUT VALIDATION

### 7.1 Request Validation

```go
type ValidationMiddleware struct {
    validator *validator.Validate
}

func (v *ValidationMiddleware) ValidateRequest(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        var req interface{}
        
        // Decode request based on endpoint
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            writeError(w, ErrInvalidJSON)
            return
        }
        
        // Validate
        if err := v.validator.Struct(req); err != nil {
            validationErrors := err.(validator.ValidationErrors)
            writeError(w, NewValidationError(validationErrors))
            return
        }
        
        next.ServeHTTP(w, r)
    })
}

// Custom validators
func registerCustomValidators(v *validator.Validate) {
    v.RegisterValidation("symbol", validateSymbol)
    v.RegisterValidation("timeframe", validateTimeframe)
    v.RegisterValidation("date_range", validateDateRange)
}
```

### 7.2 SQL Injection Prevention

```go
// ALWAYS use parameterized queries
func (r *Repository) GetBySymbol(ctx context.Context, symbol string) (*MarketData, error) {
    query := `SELECT * FROM market_data WHERE symbol = $1`
    
    var data MarketData
    err := r.db.QueryRowContext(ctx, query, symbol).Scan(&data)
    return &data, err
}

// NEVER concatenate SQL
// WRONG: query := fmt.Sprintf("SELECT * FROM market_data WHERE symbol = '%s'", symbol)
```

---

## 8. AUDIT LOGGING

### 8.1 Structure

```go
type AuditLog struct {
    ID         uuid.UUID              `json:"id"`
    Timestamp  time.Time              `json:"timestamp"`
    UserID     uuid.UUID              `json:"user_id,omitempty"`
    IP         string                 `json:"ip"`
    UserAgent  string                 `json:"user_agent"`
    Action     string                 `json:"action"`
    Entity     string                 `json:"entity"`
    EntityID   uuid.UUID              `json:"entity_id,omitempty"`
    Changes    map[string]interface{} `json:"changes,omitempty"`
    Status     string                 `json:"status"` // success, failure
    Error      string                 `json:"error,omitempty"`
}
```

### 8.2 Middleware

```go
func AuditMiddleware(auditLogger *AuditLogger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()
            
            // Wrap response writer
            wrapped := &responseWriter{ResponseWriter: w}
            
            // Process request
            next.ServeHTTP(wrapped, r)
            
            // Log
            auditLogger.Log(r.Context(), AuditLog{
                Timestamp: start,
                UserID:    GetClaims(r.Context()).UserID,
                IP:        r.RemoteAddr,
                UserAgent: r.UserAgent(),
                Action:    r.Method + " " + r.URL.Path,
                Status:    map[bool]string{true: "success", false: "failure"}[wrapped.status < 400],
            })
        })
    }
}
```

---

## 9. SECURITY HEADERS

```go
func SecurityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("X-XSS-Protection", "1; mode=block")
        w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        w.Header().Set("Content-Security-Policy", "default-src 'self'")
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        
        next.ServeHTTP(w, r)
    })
}
```

---

## 10. SECURITY CHECKLIST

### Production Deployment

- [ ] HTTPS enabled with valid certificates
- [ ] JWT secrets stored in Vault
- [ ] Database credentials rotated regularly
- [ ] API keys have appropriate rate limits
- [ ] All endpoints require authentication
- [ ] RBAC permissions enforced
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] CORS properly configured
- [ ] Security headers set
- [ ] Vault policies restrictive
- [ ] mTLS for internal services
- [ ] Secrets rotation automated

---

**Версия документации:** 3.2 Final
