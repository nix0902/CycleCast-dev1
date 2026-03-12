package tests

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"

	"github.com/cyclecast/backend/cmd/api/routes"
	"github.com/cyclecast/backend/internal/domain"
	"github.com/cyclecast/backend/pkg/logger"
)

// MockAnnualCycleService mocks the AnnualCycleService interface
type MockAnnualCycleService struct {
	mock.Mock
}

func (m *MockAnnualCycleService) Calculate(ctx context.Context, instrumentID string, minYears int) (*domain.AnnualCycleResult, error) {
	args := m.Called(ctx, instrumentID, minYears)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.AnnualCycleResult), args.Error(1)
}

func (m *MockAnnualCycleService) ValidateFTE(ctx context.Context, instrumentID string, result *domain.AnnualCycleResult) (*domain.AnnualCycleResult, error) {
	args := m.Called(ctx, instrumentID, result)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.AnnualCycleResult), args.Error(1)
}

func (m *MockAnnualCycleService) GetCurrentSignal(ctx context.Context, instrumentID string) (*domain.Signal, error) {
	args := m.Called(ctx, instrumentID)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.Signal), args.Error(1)
}

func setupTestRouter(mockService *MockAnnualCycleService) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	log := logger.New("error")
	
	handler := routes.NewSeasonalityHandler(mockService, log)
	v1 := router.Group("/api/v1")
	handler.RegisterRoutes(v1)
	
	return router
}

func TestGetSeasonality_Success(t *testing.T) {
	router := setupTestRouter(&MockAnnualCycleService{})
	
	mockService := &MockAnnualCycleService{}
	mockService.On("Calculate", mock.Anything, "SPX", 30).Return(&domain.AnnualCycleResult{
		InstrumentID:    "SPX",
		YearsAnalyzed:   45,
		TotalDataPoints: 11340,
		SeasonalProfile: []domain.SeasonalPoint{
			{
				DayOfYear:  1,
				Date:       time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC),
				AvgReturn:  0.0023,
				StdDev:     0.0089,
				WinRate:    0.62,
				SampleSize: 45,
				Percentile: 0.78,
			},
		},
		PeakDay:       185,
		TroughDay:     320,
		Amplitude:     0.045,
		LastDataPoint: time.Now(),
	}, nil)
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/SPX", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response routes.GetSeasonalityResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "SPX", response.InstrumentID)
	assert.Equal(t, 45, response.AnnualCycle.YearsAnalyzed)
	
	mockService.AssertExpectations(t)
}

func TestGetSeasonality_InvalidInstrument(t *testing.T) {
	router := setupTestRouter(&MockAnnualCycleService{})
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var response map[string]string
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "instrument_id is required", response["error"])
}

func TestGetSeasonality_NotFound(t *testing.T) {
	mockService := &MockAnnualCycleService{}
	mockService.On("Calculate", mock.Anything, "UNKNOWN", 30).Return((*domain.AnnualCycleResult)(nil), nil)
	
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/UNKNOWN", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNotFound, w.Code)
	mockService.AssertExpectations(t)
}

func TestGetCurrentSignal_Success(t *testing.T) {
	mockService := &MockAnnualCycleService{}
	mockService.On("GetCurrentSignal", mock.Anything, "SPX").Return(&domain.Signal{
		ID:              "sig_spx_20260314",
		InstrumentID:    "SPX",
		SignalType:      "BUY",
		Strength:        0.72,
		InitialStrength: 0.72,
		Timestamp:       time.Now(),
		Metadata: map[string]interface{}{
			"source":         "annual_cycle",
			"fte_validated":  true,
			"regime":         "NORMAL_VOL",
		},
	}, nil)
	
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/SPX/signal", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var signal domain.Signal
	err := json.Unmarshal(w.Body.Bytes(), &signal)
	assert.NoError(t, err)
	assert.Equal(t, "BUY", signal.SignalType)
	assert.Equal(t, 0.72, signal.Strength)
	
	mockService.AssertExpectations(t)
}

func TestGetCurrentSignal_NoSignal(t *testing.T) {
	mockService := &MockAnnualCycleService{}
	mockService.On("GetCurrentSignal", mock.Anything, "SPX").Return((*domain.Signal)(nil), nil)
	
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/SPX/signal", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNotFound, w.Code)
	mockService.AssertExpectations(t)
}

func TestGetFTEMetrics_Success(t *testing.T) {
	mockService := &MockAnnualCycleService{}
	mockService.On("Calculate", mock.Anything, "SPX", 30).Return(&domain.AnnualCycleResult{
		InstrumentID:  "SPX",
		YearsAnalyzed: 45,
		FTE: &domain.FTEResult{
			PearsonCorrelation: 0.12,
			SpearmanCorrelation: 0.11,
			KendallCorrelation: 0.09,
			DirectionAccuracy:  0.58,
			Volatility:         0.015,
			AdaptiveThreshold:  0.085,
			Status:             "VALID",
			Regime:             "NORMAL_VOL",
			LastValidated:      time.Now(),
		},
	}, nil)
	
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/SPX/fte", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var fte routes.FTEMetrics
	err := json.Unmarshal(w.Body.Bytes(), &fte)
	assert.NoError(t, err)
	assert.Equal(t, 0.12, fte.PearsonCorr)
	assert.Equal(t, "VALID", fte.Status)
	
	mockService.AssertExpectations(t)
}

func TestRecalculate_Success(t *testing.T) {
	mockService := &MockAnnualCycleService{}
	mockService.On("Calculate", mock.Anything, "SPX", 30).Return(&domain.AnnualCycleResult{
		InstrumentID:  "SPX",
		YearsAnalyzed: 45,
		FTE: &domain.FTEResult{
			Status: "VALID",
		},
	}, nil)
	
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("POST", "/api/v1/seasonality/SPX/calculate?force=true", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusAccepted, w.Code)
	
	var response routes.RecalculateResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "forced_recalculation", response.Status)
	assert.True(t, response.FTE)
	
	mockService.AssertExpectations(t)
}

func TestRecalculate_WithoutForce(t *testing.T) {
	mockService := &MockAnnualCycleService{}
	mockService.On("Calculate", mock.Anything, "SPX", 30).Return(&domain.AnnualCycleResult{
		InstrumentID:  "SPX",
		YearsAnalyzed: 45,
	}, nil)
	
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("POST", "/api/v1/seasonality/SPX/calculate", bytes.NewBuffer([]byte{}))
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusAccepted, w.Code)
	
	var response routes.RecalculateResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "completed", response.Status)
	
	mockService.AssertExpectations(t)
}

func TestHelperBuildSeasonalDaysData(t *testing.T) {
	result := &domain.AnnualCycleResult{
		SeasonalProfile: []domain.SeasonalPoint{
			{
				DayOfYear:  100,
				Date:       time.Date(2026, 4, 10, 0, 0, 0, 0, time.UTC),
				AvgReturn:  0.0015,
				StdDev:     0.0075,
				WinRate:    0.55,
				SampleSize: 30,
				Percentile: 0.65,
			},
		},
	}
	
	days := routes.BuildSeasonalDaysDataForTest(result)
	
	assert.Len(t, days, 1)
	assert.Equal(t, 100, days[0].DayOfYear)
	assert.Equal(t, "2026-04-10", days[0].Date)
	assert.Equal(t, 0.0015, days[0].AvgReturn)
}

func TestHelperBuildFTEMetrics(t *testing.T) {
	fteResult := &domain.FTEResult{
		PearsonCorrelation: 0.15,
		SpearmanCorrelation: 0.13,
		KendallCorrelation: 0.10,
		DirectionAccuracy:  0.60,
		Volatility:         0.020,
		AdaptiveThreshold:  0.090,
		Status:             "VALID",
		Regime:             "HIGH_VOL",
		LastValidated:      time.Now(),
	}
	
	metrics := routes.BuildFTEMetricsForTest(fteResult)
	
	assert.Equal(t, 0.15, metrics.PearsonCorr)
	assert.Equal(t, 0.13, metrics.SpearmanCorr)
	assert.Equal(t, "VALID", metrics.Status)
	assert.Equal(t, "HIGH_VOL", metrics.Regime)
}

func TestHelperCalculateDataCompleteness(t *testing.T) {
	// Test with complete data
	result := &domain.AnnualCycleResult{
		YearsAnalyzed:   10,
		TotalDataPoints: 2520, // 10 years * 252 days
	}
	completeness := routes.CalculateDataCompletenessForTest(result)
	assert.Equal(t, 1.0, completeness)
	
	// Test with partial data
	result2 := &domain.AnnualCycleResult{
		YearsAnalyzed:   10,
		TotalDataPoints: 1260, // 50% of expected
	}
	completeness2 := routes.CalculateDataCompletenessForTest(result2)
	assert.Equal(t, 0.5, completeness2)
	
	// Test with nil result
	completeness3 := routes.CalculateDataCompletenessForTest(nil)
	assert.Equal(t, 0.0, completeness3)
}

func TestWebSocketEndpoint_Structure(t *testing.T) {
	// Test that WebSocket endpoint exists and accepts upgrade
	mockService := &MockAnnualCycleService{}
	router := setupTestRouter(mockService)
	
	req, _ := http.NewRequest("GET", "/api/v1/seasonality/SPX/stream", nil)
	req.Header.Set("Connection", "Upgrade")
	req.Header.Set("Upgrade", "websocket")
	req.Header.Set("Sec-WebSocket-Version", "13")
	req.Header.Set("Sec-WebSocket-Key", "dGhlIHNhbXBsZSBub25jZQ==")
	
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	// WebSocket upgrade returns 101 Switching Protocols or handles gracefully in test mode
	// In test mode without actual WebSocket server, we expect it to handle the request
	assert.Contains(t, []int{http.StatusOK, http.StatusSwitchingProtocols}, w.Code)
}
