// Package main is the entry point for the CycleCast API server
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"github.com/cyclecast/backend/internal/infrastructure/config"
	"github.com/cyclecast/backend/internal/infrastructure/database"
	"github.com/cyclecast/backend/internal/infrastructure/grpc"
	"github.com/cyclecast/backend/internal/infrastructure/redis"
	"github.com/cyclecast/backend/internal/repository/postgres"
	"github.com/cyclecast/backend/internal/service"
	"github.com/cyclecast/backend/pkg/logger"

	"github.com/cyclecast/backend/cmd/api/routes"
)

var Version = "dev"

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize logger
	log := logger.New(cfg.LogLevel)
	log.Info("Starting CycleCast API", "version", Version, "env", cfg.Environment)

	// Initialize database connection
	dbPool, err := database.NewPostgresPool(cfg.DatabaseURL)
	if err != nil {
		log.Fatal("Failed to connect to database", "error", err)
	}
	defer dbPool.Close()

	// Initialize Redis client
	rdb := redis.NewClient(cfg.RedisURL)
	defer rdb.Close()

	// Initialize repositories
	instrumentRepo := postgres.NewInstrumentRepository(dbPool)
	marketDataRepo := postgres.NewMarketDataRepository(dbPool)
	cotRepo := postgres.NewCOTRepository(dbPool)
	signalRepo := postgres.NewSignalRepository(dbPool)
	cacheRepo := redis.NewCacheRepository(rdb)

	// Initialize Python gRPC client for quant services
	quantClient, err := grpc.NewQuantClient(cfg.QuantServiceURL)
	if err != nil {
		log.Warn("Failed to connect to quant service", "error", err)
	}

	// Initialize services
	marketDataService := service.NewMarketDataService(marketDataRepo, cacheRepo)
	annualCycleService := service.NewAnnualCycleService(marketDataRepo, quantClient)
	cycleAnalysisService := service.NewCycleAnalysisService(quantClient)
	compositeLineService := service.NewCompositeLineService(cycleAnalysisService)
	phenomService := service.NewPhenomenologicalService(quantClient)
	cotService := service.NewCOTService(cotRepo)
	signalAggService := service.NewSignalAggregationService(annualCycleService, compositeLineService, phenomService, cotService)
	riskService := service.NewRiskManagementService()
	backtestService := service.NewBacktestService(marketDataRepo, quantClient)

	// Initialize Gin router
	router := setupRouter(cfg, log, instrumentRepo, marketDataService, annualCycleService,
		cycleAnalysisService, compositeLineService, phenomService, cotService,
		signalAggService, riskService, backtestService, signalRepo)

	// Create HTTP server
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.APIPort),
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in goroutine
	go func() {
		log.Info("API server starting", "port", cfg.APIPort)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal("Server failed", "error", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Info("Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Error("Server shutdown failed", "error", err)
	}

	log.Info("Server exited")
}

func setupRouter(cfg *config.Config, log logger.Logger,
	instrumentRepo repository.InstrumentRepository,
	marketDataService service.MarketDataService,
	annualCycleService service.AnnualCycleService,
	cycleAnalysisService service.CycleAnalysisService,
	compositeLineService service.CompositeLineService,
	phenomService service.PhenomenologicalService,
	cotService service.COTService,
	signalAggService service.SignalAggregationService,
	riskService service.RiskManagementService,
	backtestService service.BacktestService,
	signalRepo repository.SignalRepository) *gin.Engine {

	gin.SetMode(cfg.GinMode)
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(logger.Middleware(log))

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "version": Version})
	})

	// API v1 routes
	v1 := router.Group("/api/v1")
	{
		// Instruments
		instruments := v1.Group("/instruments")
		{
			instruments.GET("", func(c *gin.Context) {
				// TODO: Implement list instruments
				c.JSON(http.StatusOK, gin.H{"instruments": []interface{}{}})
			})
			instruments.GET("/:id", func(c *gin.Context) {
				// TODO: Implement get instrument
				c.JSON(http.StatusOK, gin.H{})
			})
		}

		// Market Data
		market := v1.Group("/market")
		{
			market.POST("/import", func(c *gin.Context) {
				// TODO: Implement import data
				c.JSON(http.StatusAccepted, gin.H{"status": "processing"})
			})
			market.GET("/history", func(c *gin.Context) {
				// TODO: Implement get history
				c.JSON(http.StatusOK, gin.H{"data": []interface{}{}})
			})
		}

		// Analysis
		analysis := v1.Group("/analysis")
		{
			analysis.GET("/annual-cycle/:instrument_id", func(c *gin.Context) {
				// TODO: Implement annual cycle analysis
				c.JSON(http.StatusOK, gin.H{})
			})
			analysis.GET("/cycles/:instrument_id", func(c *gin.Context) {
				// TODO: Implement cycle analysis
				c.JSON(http.StatusOK, gin.H{})
			})
			analysis.GET("/composite/:instrument_id", func(c *gin.Context) {
				// TODO: Implement composite line
				c.JSON(http.StatusOK, gin.H{})
			})
			analysis.GET("/analogies/:instrument_id", func(c *gin.Context) {
				// TODO: Implement historical analogies
				c.JSON(http.StatusOK, gin.H{})
			})
		}

		// Signals
		signals := v1.Group("/signals")
		{
			signals.GET("/:instrument_id", func(c *gin.Context) {
				// TODO: Implement get signals
				c.JSON(http.StatusOK, gin.H{"signals": []interface{}{}})
			})
			signals.POST("/aggregate/:instrument_id", func(c *gin.Context) {
				// TODO: Implement signal aggregation
				c.JSON(http.StatusOK, gin.H{})
			})
		}

		// Backtesting
		backtest := v1.Group("/backtest")
		{
			backtest.POST("/run", func(c *gin.Context) {
				// TODO: Implement run backtest
				c.JSON(http.StatusAccepted, gin.H{"job_id": "pending"})
			})
			backtest.GET("/results/:job_id", func(c *gin.Context) {
				// TODO: Implement get backtest results
				c.JSON(http.StatusOK, gin.H{})
			})
		}

		// Risk Management
		risk := v1.Group("/risk")
		{
			risk.POST("/position-size", func(c *gin.Context) {
				// TODO: Implement position size calculation
				c.JSON(http.StatusOK, gin.H{})
			})
		}

		// Seasonality Dashboard routes
		seasonalityHandler := routes.NewSeasonalityHandler(annualCycleService, log)
		seasonalityHandler.RegisterRoutes(v1)
	}

	return router
}
