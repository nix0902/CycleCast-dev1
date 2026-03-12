// Package routes provides HTTP route handlers for the Seasonality Dashboard
package routes

import (
	"context"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	"github.com/cyclecast/backend/internal/domain"
	"github.com/cyclecast/backend/internal/service"
	"github.com/cyclecast/backend/pkg/logger"
)

// SeasonalityHandler handles seasonality-related HTTP requests
type SeasonalityHandler struct {
	annualCycleService service.AnnualCycleService
	log                logger.Logger
	wsUpgrader         websocket.Upgrader
	activeConnections  sync.Map // map[string]*websocket.Conn
}

// NewSeasonalityHandler creates a new seasonality route handler
func NewSeasonalityHandler(
	annualCycleService service.AnnualCycleService,
	log logger.Logger,
) *SeasonalityHandler {
	return &SeasonalityHandler{
		annualCycleService: annualCycleService,
		log:                log,
		wsUpgrader: websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 1024,
			CheckOrigin: func(r *http.Request) bool {
				// Allow all origins in development; restrict in production
				return true
			},
		},
	}
}

// RegisterRoutes registers seasonality routes on the given router group
func (h *SeasonalityHandler) RegisterRoutes(v1 *gin.RouterGroup) {
	seasonality := v1.Group("/seasonality")
	{
		// GET /api/v1/seasonality/{instrument} - Get seasonality analysis for instrument
		seasonality.GET("/:instrument_id", h.GetSeasonality)

		// GET /api/v1/seasonality/{instrument}/signal - Get current seasonality signal
		seasonality.GET("/:instrument_id/signal", h.GetCurrentSignal)

		// GET /api/v1/seasonality/{instrument}/fte - Get FTE validation metrics
		seasonality.GET("/:instrument_id/fte", h.GetFTEMetrics)

		// POST /api/v1/seasonality/{instrument}/calculate - Trigger recalculation
		seasonality.POST("/:instrument_id/calculate", h.Recalculate)

		// WebSocket: WS /api/v1/seasonality/{instrument}/stream - Real-time updates
		seasonality.GET("/:instrument_id/stream", h.StreamUpdates)
	}
}

// GetSeasonalityResponse represents the seasonality analysis response
type GetSeasonalityResponse struct {
	InstrumentID  string                 `json:"instrument_id"`
	AnnualCycle   *domain.AnnualCycleResult `json:"annual_cycle"`
	SeasonalDays  []SeasonalDayData      `json:"seasonal_days"`
	FTE           *FTEMetrics            `json:"fte,omitempty"`
	LastUpdated   time.Time              `json:"last_updated"`
	DataQuality   DataQualityInfo        `json:"data_quality"`
}

// SeasonalDayData represents daily seasonality data point
type SeasonalDayData struct {
	DayOfYear     int     `json:"day_of_year"`
	Date          string  `json:"date"`
	AvgReturn     float64 `json:"avg_return"`
	StdDev        float64 `json:"std_dev"`
	WinRate       float64 `json:"win_rate"`
	SampleSize    int     `json:"sample_size"`
	Percentile    float64 `json:"percentile"`
}

// FTEMetrics represents Forecast Theoretical Efficiency metrics
type FTEMetrics struct {
	PearsonCorr    float64 `json:"pearson_correlation"`
	SpearmanCorr   float64 `json:"spearman_correlation"`
	KendallCorr    float64 `json:"kendall_correlation"`
	DirectionAcc   float64 `json:"direction_accuracy"`
	Volatility     float64 `json:"volatility"`
	Threshold      float64 `json:"adaptive_threshold"`
	Status         string  `json:"status"` // VALID, INVALID, BROKEN, INSUFFICIENT_DATA
	Regime         string  `json:"regime,omitempty"`
	LastValidated  time.Time `json:"last_validated"`
}

// DataQualityInfo represents data quality assessment
type DataQualityInfo struct {
	YearsAvailable   int     `json:"years_available"`
	DataCompleteness float64 `json:"data_completeness"` // 0.0 to 1.0
	LastDataPoint    time.Time `json:"last_data_point"`
	Warnings         []string `json:"warnings,omitempty"`
}

// GetSeasonality handles GET /api/v1/seasonality/{instrument_id}
// @Summary Get seasonality analysis for instrument
// @Description Returns annual cycle analysis, seasonal patterns, and FTE metrics
// @Tags seasonality
// @Accept json
// @Produce json
// @Param instrument_id path string true "Instrument ID (e.g., SPX, GC, BTC)"
// @Param min_years query int false "Minimum years of data" default(30)
// @Success 200 {object} GetSeasonalityResponse
// @Failure 400 {object} ErrorResponse
// @Failure 404 {object} ErrorResponse
// @Failure 500 {object} ErrorResponse
// @Router /api/v1/seasonality/{instrument_id} [get]
func (h *SeasonalityHandler) GetSeasonality(c *gin.Context) {
	instrumentID := c.Param("instrument_id")
	if instrumentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "instrument_id is required"})
		return
	}

	// Parse optional query parameter
	minYears := 30
	if years := c.Query("min_years"); years != "" {
		if _, err := fmt.Sscanf(years, "%d", &minYears); err != nil {
			h.log.Warn("Invalid min_years parameter", "value", years, "error", err)
		}
	}

	ctx := c.Request.Context()

	// Calculate annual cycle
	result, err := h.annualCycleService.Calculate(ctx, instrumentID, minYears)
	if err != nil {
		h.log.Error("Failed to calculate annual cycle", "instrument", instrumentID, "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to calculate seasonality"})
		return
	}

	if result == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "No seasonality data found"})
		return
	}

	// Build seasonal days data from result
	seasonalDays := buildSeasonalDaysData(result)

	// Get FTE metrics if available
	var fteMetrics *FTEMetrics
	if result.FTE != nil {
		fteMetrics = buildFTEMetrics(result.FTE)
	}

	// Build response
	response := GetSeasonalityResponse{
		InstrumentID: instrumentID,
		AnnualCycle:  result,
		SeasonalDays: seasonalDays,
		FTE:          fteMetrics,
		LastUpdated:  time.Now(),
		DataQuality: DataQualityInfo{
			YearsAvailable:   result.YearsAnalyzed,
			DataCompleteness: calculateDataCompleteness(result),
			LastDataPoint:    result.LastDataPoint,
			Warnings:         result.Warnings,
		},
	}

	c.JSON(http.StatusOK, response)
}

// GetCurrentSignal handles GET /api/v1/seasonality/{instrument_id}/signal
// @Summary Get current seasonality signal
// @Description Returns the current trading signal based on seasonality analysis
// @Tags seasonality
// @Produce json
// @Param instrument_id path string true "Instrument ID"
// @Success 200 {object} domain.Signal
// @Failure 404 {object} ErrorResponse
// @Failure 500 {object} ErrorResponse
// @Router /api/v1/seasonality/{instrument_id}/signal [get]
func (h *SeasonalityHandler) GetCurrentSignal(c *gin.Context) {
	instrumentID := c.Param("instrument_id")
	if instrumentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "instrument_id is required"})
		return
	}

	ctx := c.Request.Context()

	signal, err := h.annualCycleService.GetCurrentSignal(ctx, instrumentID)
	if err != nil {
		h.log.Error("Failed to get current signal", "instrument", instrumentID, "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve signal"})
		return
	}

	if signal == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "No active signal"})
		return
	}

	c.JSON(http.StatusOK, signal)
}

// GetFTEMetrics handles GET /api/v1/seasonality/{instrument_id}/fte
// @Summary Get FTE validation metrics
// @Description Returns Forecast Theoretical Efficiency metrics for seasonality validation
// @Tags seasonality
// @Produce json
// @Param instrument_id path string true "Instrument ID"
// @Success 200 {object} FTEMetrics
// @Failure 404 {object} ErrorResponse
// @Failure 500 {object} ErrorResponse
// @Router /api/v1/seasonality/{instrument_id}/fte [get]
func (h *SeasonalityHandler) GetFTEMetrics(c *gin.Context) {
	instrumentID := c.Param("instrument_id")
	if instrumentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "instrument_id is required"})
		return
	}

	ctx := c.Request.Context()

	// Calculate to get FTE validation
	result, err := h.annualCycleService.Calculate(ctx, instrumentID, 30)
	if err != nil {
		h.log.Error("Failed to calculate for FTE", "instrument", instrumentID, "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to calculate FTE metrics"})
		return
	}

	if result == nil || result.FTE == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "FTE metrics not available"})
		return
	}

	fteMetrics := buildFTEMetrics(result.FTE)
	c.JSON(http.StatusOK, fteMetrics)
}

// Recalculate handles POST /api/v1/seasonality/{instrument_id}/calculate
// @Summary Trigger seasonality recalculation
// @Description Forces recalculation of seasonality analysis for the instrument
// @Tags seasonality
// @Accept json
// @Produce json
// @Param instrument_id path string true "Instrument ID"
// @Param force query bool false "Force recalculation even if cached" default(false)
// @Success 202 {object} RecalculateResponse
// @Failure 400 {object} ErrorResponse
// @Failure 500 {object} ErrorResponse
// @Router /api/v1/seasonality/{instrument_id}/calculate [post]
func (h *SeasonalityHandler) Recalculate(c *gin.Context) {
	instrumentID := c.Param("instrument_id")
	if instrumentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "instrument_id is required"})
		return
	}

	force := c.Query("force") == "true"

	ctx := c.Request.Context()

	// Trigger calculation (service handles caching logic)
	result, err := h.annualCycleService.Calculate(ctx, instrumentID, 30)
	if err != nil {
		h.log.Error("Failed to recalculate seasonality", "instrument", instrumentID, "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Recalculation failed"})
		return
	}

	response := RecalculateResponse{
		InstrumentID: instrumentID,
		Status:       "completed",
		YearsAnalyzed: result.YearsAnalyzed,
		FTE:          result.FTE != nil && result.FTE.Status == "VALID",
		Timestamp:    time.Now(),
	}

	if force {
		response.Status = "forced_recalculation"
	}

	c.JSON(http.StatusAccepted, response)
}

// RecalculateResponse represents recalculation result
type RecalculateResponse struct {
	InstrumentID  string    `json:"instrument_id"`
	Status        string    `json:"status"`
	YearsAnalyzed int       `json:"years_analyzed"`
	FTE           bool      `json:"fte_valid"`
	Timestamp     time.Time `json:"timestamp"`
}

// StreamUpdates handles WebSocket connection for real-time seasonality updates
// @Summary WebSocket stream for real-time seasonality updates
// @Description Establishes WebSocket connection for push notifications on seasonality changes
// @Tags seasonality
// @Param instrument_id path string true "Instrument ID"
// @Success 101 "Switching Protocols"
// @Failure 400 {object} ErrorResponse
// @Router /api/v1/seasonality/{instrument_id}/stream [get]
func (h *SeasonalityHandler) StreamUpdates(c *gin.Context) {
	instrumentID := c.Param("instrument_id")
	if instrumentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "instrument_id is required"})
		return
	}

	// Upgrade HTTP connection to WebSocket
	conn, err := h.wsUpgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		h.log.Error("WebSocket upgrade failed", "instrument", instrumentID, "error", err)
		return
	}
	defer conn.Close()

	// Store connection
	connectionID := fmt.Sprintf("%s:%s", instrumentID, c.ClientIP())
	h.activeConnections.Store(connectionID, conn)
	defer h.activeConnections.Delete(connectionID)

	h.log.Info("WebSocket connection established", "connection_id", connectionID)

	// Send initial connection confirmation
	if err := conn.WriteJSON(gin.H{
		"type":       "connected",
		"instrument": instrumentID,
		"timestamp":  time.Now(),
	}); err != nil {
		h.log.Warn("Failed to send connection confirmation", "error", err)
		return
	}

	// Listen for client messages and send periodic updates
	ctx, cancel := context.WithCancel(c.Request.Context())
	defer cancel()

	// Start background update sender
	go h.sendPeriodicUpdates(ctx, conn, instrumentID)

	// Handle incoming messages (ping/pong, control)
	for {
		select {
		case <-ctx.Done():
			return
		default:
			// Set read deadline
			conn.SetReadDeadline(time.Now().Add(60 * time.Second))

			var msg map[string]interface{}
			if err := conn.ReadJSON(&msg); err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					h.log.Warn("WebSocket read error", "connection_id", connectionID, "error", err)
				}
				return
			}

			// Handle control messages
			if msgType, ok := msg["type"].(string); ok {
				switch msgType {
				case "ping":
					_ = conn.WriteJSON(gin.H{"type": "pong", "timestamp": time.Now()})
				case "subscribe":
					h.log.Info("Client subscribed", "connection_id", connectionID)
				case "unsubscribe":
					return
				}
			}
		}
	}
}

// sendPeriodicUpdates sends periodic seasonality updates via WebSocket
func (h *SeasonalityHandler) sendPeriodicUpdates(ctx context.Context, conn *websocket.Conn, instrumentID string) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			// Get current signal for update
			signal, err := h.annualCycleService.GetCurrentSignal(ctx, instrumentID)
			if err != nil {
				h.log.Debug("Failed to get signal for WebSocket update", "instrument", instrumentID, "error", err)
				continue
			}

			if signal == nil {
				continue
			}

			// Send update
			update := gin.H{
				"type":       "signal_update",
				"instrument": instrumentID,
				"signal":     signal,
				"timestamp":  time.Now(),
			}

			if err := conn.WriteJSON(update); err != nil {
				h.log.Warn("Failed to send WebSocket update", "error", err)
				return
			}
		}
	}
}

// Helper functions

// BuildSeasonalDaysDataForTest exports buildSeasonalDaysData for testing
func BuildSeasonalDaysDataForTest(result *domain.AnnualCycleResult) []SeasonalDayData {
	return buildSeasonalDaysData(result)
}

func buildSeasonalDaysData(result *domain.AnnualCycleResult) []SeasonalDayData {
	if result == nil || len(result.SeasonalProfile) == 0 {
		return []SeasonalDayData{}
	}

	days := make([]SeasonalDayData, 0, len(result.SeasonalProfile))
	for _, point := range result.SeasonalProfile {
		days = append(days, SeasonalDayData{
			DayOfYear:  point.DayOfYear,
			Date:       point.Date.Format("2006-01-02"),
			AvgReturn:  point.AvgReturn,
			StdDev:     point.StdDev,
			WinRate:    point.WinRate,
			SampleSize: point.SampleSize,
			Percentile: point.Percentile,
		})
	}
	return days
}

// BuildFTEMetricsForTest exports buildFTEMetrics for testing
func BuildFTEMetricsForTest(fte *domain.FTEResult) *FTEMetrics {
	return buildFTEMetrics(fte)
}

func buildFTEMetrics(fte *domain.FTEResult) *FTEMetrics {
	if fte == nil {
		return nil
	}

	return &FTEMetrics{
		PearsonCorr:   fte.PearsonCorrelation,
		SpearmanCorr:  fte.SpearmanCorrelation,
		KendallCorr:   fte.KendallCorrelation,
		DirectionAcc:  fte.DirectionAccuracy,
		Volatility:    fte.Volatility,
		Threshold:     fte.AdaptiveThreshold,
		Status:        string(fte.Status),
		Regime:        fte.Regime,
		LastValidated: fte.LastValidated,
	}
}

// CalculateDataCompletenessForTest exports calculateDataCompleteness for testing
func CalculateDataCompletenessForTest(result *domain.AnnualCycleResult) float64 {
	return calculateDataCompleteness(result)
}

func calculateDataCompleteness(result *domain.AnnualCycleResult) float64 {
	if result == nil || result.YearsAnalyzed == 0 {
		return 0.0
	}
	// Simple heuristic: assume 252 trading days per year
	expectedDays := result.YearsAnalyzed * 252
	if result.TotalDataPoints == 0 {
		return 0.0
	}
	completeness := float64(result.TotalDataPoints) / float64(expectedDays)
	if completeness > 1.0 {
		completeness = 1.0
	}
	return completeness
}

// ErrorResponse represents a standard error response
type ErrorResponse struct {
	Error   string `json:"error"`
	Details string `json:"details,omitempty"`
	Code    int    `json:"code,omitempty"`
}
