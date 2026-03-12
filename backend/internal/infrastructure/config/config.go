// Package config handles application configuration
package config

import (
	"fmt"
	"os"

	"github.com/caarlos0/env/v10"
)

// Config holds all application configuration
type Config struct {
	// Server
	Environment   string `env:"ENV" envDefault:"development"`
	APIPort       int    `env:"API_PORT" envDefault:"8080"`
	GinMode       string `env:"GIN_MODE" envDefault:"debug"`
	LogLevel      string `env:"LOG_LEVEL" envDefault:"info"`

	// Database
	DatabaseURL string `env:"DATABASE_URL" envDefault:"postgres://cyclecast:cyclecast@localhost:5432/cyclecast?sslmode=disable"`

	// Redis
	RedisURL string `env:"REDIS_URL" envDefault:"redis://localhost:6379/0"`

	// Python Quant Service (gRPC)
	QuantServiceURL string `env:"QUANT_SERVICE_URL" envDefault:"localhost:9090"`

	// External APIs
	YahooAPIKey     string `env:"YAHOO_API_KEY"`
	AlphaVantageKey string `env:"ALPHA_VANTAGE_KEY"`
	CFTCAPIKey      string `env:"CFTC_API_KEY"`

	// Security
	JWTSecret string `env:"JWT_SECRET"`
	VaultAddr string `env:"VAULT_ADDR"`
}

// Load reads configuration from environment variables
func Load() (*Config, error) {
	cfg := &Config{}
	if err := env.Parse(cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	// Validate required fields
	if cfg.Environment == "production" && cfg.JWTSecret == "" {
		return nil, fmt.Errorf("JWT_SECRET is required in production")
	}

	return cfg, nil
}

// IsProduction returns true if running in production mode
func (c *Config) IsProduction() bool {
	return c.Environment == "production"
}

// IsDevelopment returns true if running in development mode
func (c *Config) IsDevelopment() bool {
	return c.Environment == "development"
}

// GetEnv returns the value of an environment variable or default
func GetEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
