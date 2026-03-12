// Package logger provides structured logging
package logger

import (
	"os"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Logger is a structured logger interface
type Logger interface {
	Debug(msg string, fields ...zap.Field)
	Info(msg string, fields ...zap.Field)
	Warn(msg string, fields ...zap.Field)
	Error(msg string, fields ...zap.Field)
	Fatal(msg string, fields ...zap.Field)
	With(fields ...zap.Field) Logger
}

type zapLogger struct {
	*zap.SugaredLogger
}

// New creates a new logger with the specified level
func New(level string) Logger {
	zapLevel := zap.InfoLevel
	switch level {
	case "debug":
		zapLevel = zap.DebugLevel
	case "warn":
		zapLevel = zap.WarnLevel
	case "error":
		zapLevel = zap.ErrorLevel
	}

	config := zap.NewProductionConfig()
	config.Level = zap.NewAtomicLevelAt(zapLevel)
	config.EncoderConfig.TimeKey = "timestamp"
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	logger, err := config.Build()
	if err != nil {
		// Fallback to default logger
		logger = zap.NewNop()
	}

	return &zapLogger{logger.Sugar()}
}

// Middleware creates Gin middleware for request logging
func Middleware(log Logger) func(c interface{}) {
	return func(c interface{}) {
		// TODO: Implement Gin middleware
		// This is a placeholder - actual implementation would use gin.Context
	}
}

// Fields helper functions
func String(key, value string) zap.Field        { return zap.String(key, value) }
func Int(key string, value int) zap.Field       { return zap.Int(key, value) }
func Int64(key string, value int64) zap.Field   { return zap.Int64(key, value) }
func Float64(key string, value float64) zap.Field { return zap.Float64(key, value) }
func Bool(key string, value bool) zap.Field     { return zap.Bool(key, value) }
func Error(err error) zap.Field                 { return zap.Error(err) }
func Any(key string, value interface{}) zap.Field { return zap.Any(key, value) }
