// Package grpc handles gRPC client connections to Python quant service
package grpc

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// QuantClient wraps gRPC connection to Python quant service
type QuantClient struct {
	conn   *grpc.ClientConn
	addr   string
	cancel context.CancelFunc
}

// NewQuantClient creates a new gRPC client for the quant service
func NewQuantClient(addr string) (*QuantClient, error) {
	ctx, cancel := context.WithCancel(context.Background())

	conn, err := grpc.NewClient(addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(grpc.WaitForReady(true)),
		grpc.WithTimeout(30*time.Second),
	)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to connect to quant service: %w", err)
	}

	return &QuantClient{
		conn:   conn,
		addr:   addr,
		cancel: cancel,
	}, nil
}

// Close gracefully closes the gRPC connection
func (c *QuantClient) Close() error {
	if c.cancel != nil {
		c.cancel()
	}
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// HealthCheck verifies connection to quant service
func (c *QuantClient) HealthCheck(ctx context.Context) error {
	// TODO: Implement actual health check via gRPC reflection or custom endpoint
	return nil
}

// ContextWithTimeout creates a context with default timeout for quant calls
func (c *QuantClient) ContextWithTimeout(parent context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(parent, 60*time.Second)
}
