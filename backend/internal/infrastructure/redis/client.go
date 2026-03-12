// Package redis handles Redis client initialization
package redis

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// NewClient creates a new Redis client
func NewClient(redisURL string) *redis.Client {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		// Fallback to default
		return redis.NewClient(&redis.Options{
			Addr:         "localhost:6379",
			DB:           0,
			MaxRetries:   3,
			MinRetryBackoff: 8 * time.Millisecond,
			MaxRetryBackoff: 512 * time.Millisecond,
			PoolSize:     10,
			PoolTimeout:  30 * time.Second,
		})
	}

	return redis.NewClient(opts)
}

// HealthCheck verifies Redis connection
func HealthCheck(ctx context.Context, client *redis.Client) error {
	if client == nil {
		return fmt.Errorf("redis client is nil")
	}
	return client.Ping(ctx).Err()
}
