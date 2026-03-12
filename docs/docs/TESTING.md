# TESTING

> **Версия:** 3.2 Final | **CycleCast Testing Strategy**

---

## 1. ОБЩАЯ СТРАТЕГИЯ

### Testing Pyramid

```
           ┌──────────────┐
           │     E2E      │  5%
           │   Tests      │
           ├──────────────┤
           │ Integration  │  25%
           │    Tests     │
           ├──────────────┤
           │    Unit      │  70%
           │    Tests     │
           └──────────────┘
```

### Coverage Requirements

| Тип | Цель | Минимум |
|-----|------|---------|
| Unit Tests | 80% | 70% |
| Integration Tests | 60% | 50% |
| E2E Tests | Key flows | Critical paths |

---

## 2. GO BACKEND TESTING

### 2.1 Unit Tests

#### Структура теста

```go
// service_test.go
package marketdata

import (
    "context"
    "testing"
    
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/mock"
)

func TestService_GetMarketData(t *testing.T) {
    tests := []struct {
        name    string
        symbol  string
        opts    GetOptions
        mockFn  func(*MockRepository)
        want    *MarketData
        wantErr error
    }{
        {
            name:   "success",
            symbol: "BTC-USD",
            opts:   GetOptions{Timeframe: "1d"},
            mockFn: func(m *MockRepository) {
                m.On("GetBySymbol", mock.Anything, "BTC-USD", mock.Anything).
                    Return(&MarketData{Symbol: "BTC-USD"}, nil)
            },
            want: &MarketData{Symbol: "BTC-USD"},
        },
        {
            name:    "not found",
            symbol:  "INVALID",
            opts:    GetOptions{Timeframe: "1d"},
            mockFn: func(m *MockRepository) {
                m.On("GetBySymbol", mock.Anything, "INVALID", mock.Anything).
                    Return(nil, ErrNotFound)
            },
            wantErr: ErrNotFound,
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Arrange
            repo := NewMockRepository(t)
            tt.mockFn(repo)
            svc := NewService(repo)
            
            // Act
            got, err := svc.Get(context.Background(), tt.symbol, tt.opts)
            
            // Assert
            if tt.wantErr != nil {
                assert.ErrorIs(t, err, tt.wantErr)
                assert.Nil(t, got)
            } else {
                assert.NoError(t, err)
                assert.Equal(t, tt.want, got)
            }
            repo.AssertExpectations(t)
        })
    }
}
```

#### Table-Driven Tests

```go
func TestCalculateFTE(t *testing.T) {
    tests := []struct {
        name         string
        correlation  float64
        threshold    float64
        wantValid    bool
        wantStatus   string
    }{
        {"valid high correlation", 0.15, 0.08, true, "PASS"},
        {"valid at threshold", 0.08, 0.08, true, "PASS"},
        {"invalid below threshold", 0.05, 0.08, false, "FAIL"},
        {"negative correlation", -0.1, 0.08, false, "FAIL"},
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := CalculateFTE(tt.correlation, tt.threshold)
            assert.Equal(t, tt.wantValid, result.IsValid)
            assert.Equal(t, tt.wantStatus, result.Status)
        })
    }
}
```

#### Mock Generation

```bash
# Install mockgen
go install github.com/stretchr/mock/mockgen@latest

# Generate mocks (в Makefile)
mockgen -source=service.go -destination=mock_service.go -package=mocks
mockgen -source=repository.go -destination=mock_repository.go -package=mocks
```

### 2.2 Integration Tests

```go
// integration_test.go
//go:build integration

package marketdata_test

import (
    "context"
    "testing"
    
    "github.com/testcontainers/testcontainers-go"
    "github.com/testcontainers/testcontainers-go/modules/postgres"
)

func TestService_Integration_GetMarketData(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }
    
    // Setup PostgreSQL container
    ctx := context.Background()
    pgContainer, err := postgres.Run(ctx, "postgres:16")
    require.NoError(t, err)
    defer pgContainer.Terminate(ctx)
    
    // Get connection string
    connStr, err := pgContainer.ConnectionString(ctx, "sslmode=disable")
    require.NoError(t, err)
    
    // Setup service with real DB
    db, err := sql.Open("pgx", connStr)
    require.NoError(t, err)
    defer db.Close()
    
    repo := repository.NewPgRepository(db)
    svc := service.New(repo)
    
    // Test
    data, err := svc.Get(ctx, "BTC-USD", service.GetOptions{})
    require.NoError(t, err)
    assert.NotNil(t, data)
}
```

### 2.3 Benchmarks

```go
func BenchmarkCalculateAnnualCycle(b *testing.B) {
    prices := generateTestPrices(10000)
    
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        CalculateAnnualCycle(prices, 10)
    }
}

func BenchmarkQSpectrum(b *testing.B) {
    prices := generateTestPrices(5000)
    
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        CalculateQSpectrum(prices, QSpectrumConfig{
            MinPeriod: 10,
            MaxPeriod: 200,
        })
    }
}
```

---

## 3. PYTHON QUANT TESTING

### 3.1 Unit Tests

```python
# test_qspectrum.py
import pytest
import numpy as np
from qspectrum import QSpectrumAnalyzer


@pytest.fixture
def sample_prices():
    """Generate sample price data with known cycles."""
    t = np.linspace(0, 10 * np.pi, 1000)
    prices = (
        100 + 
        10 * np.sin(2 * np.pi * t / 14) +    # 14-day cycle
        5 * np.sin(2 * np.pi * t / 28) +     # 28-day cycle
        np.random.randn(1000) * 2            # noise
    )
    return prices


class TestQSpectrumAnalyzer:
    
    def test_detect_14_day_cycle(self, sample_prices):
        """Should detect the 14-day dominant cycle."""
        analyzer = QSpectrumAnalyzer(min_period=10, max_period=50)
        result = analyzer.analyze(sample_prices)
        
        # Check that 14 is in top 3 cycles
        periods = [c["period"] for c in result["top3"]]
        assert 14 in periods or 15 in periods  # ±1 tolerance
    
    def test_energy_calculation(self, sample_prices):
        """Energy should be between 0 and 1."""
        analyzer = QSpectrumAnalyzer()
        result = analyzer.analyze(sample_prices)
        
        for cycle in result["cycles"]:
            assert 0 <= cycle["energy"] <= 1
    
    def test_insufficient_data_raises(self):
        """Should raise error for insufficient data."""
        prices = np.random.randn(50)  # Too short
        
        with pytest.raises(InsufficientDataError):
            QSpectrumAnalyzer().analyze(prices)
    
    @pytest.mark.parametrize("period,expected", [
        (14, "short"),
        (42, "medium"),
        (98, "long"),
    ])
    def test_cycle_classification(self, period, expected):
        """Should classify cycles correctly."""
        analyzer = QSpectrumAnalyzer()
        classification = analyzer.classify_cycle(period)
        assert classification == expected
```

### 3.2 Fixtures

```python
# conftest.py
import pytest
import numpy as np


@pytest.fixture
def btc_prices():
    """Real BTC price data for testing."""
    return np.array([...])  # Actual historical data


@pytest.fixture
def synthetic_cycle():
    """Generate synthetic price with known cycle."""
    def _make(period, amplitude, noise=0.1):
        t = np.linspace(0, 10 * np.pi, 1000)
        return amplitude * np.sin(2 * np.pi * t / period) + np.random.randn(1000) * noise
    return _make


@pytest.fixture
def mock_grpc_stub(mocker):
    """Mock gRPC stub for testing."""
    return mocker.Mock()
```

### 3.3 Property-Based Testing

```python
# test_qspectrum_properties.py
from hypothesis import given, strategies as st
import numpy as np
from qspectrum import calculate_cyclic_correlation


@given(
    period=st.integers(min_value=10, max_value=100),
    n_points=st.integers(min_value=200, max_value=1000)
)
def test_cyclic_correlation_range(period, n_points):
    """Cyclic correlation should be in valid range."""
    prices = np.random.randn(n_points)
    corr = calculate_cyclic_correlation(prices, period)
    
    # Correlation should be finite
    assert np.isfinite(corr)
    
    # With random data, correlation should be small
    assert abs(corr) < 0.5


@given(
    prices=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False),
        min_size=100,
        max_size=1000
    )
)
def test_normalize_produces_valid_range(prices):
    """Normalization should produce values in [0, 1]."""
    prices = np.array(prices)
    normalized = normalize(prices)
    
    assert np.all(normalized >= 0)
    assert np.all(normalized <= 1)
    assert np.all(np.isfinite(normalized))
```

---

## 4. BACKTEST VALIDATION

### 4.1 Walk-Forward Tests

```go
func TestBacktest_WalkForward(t *testing.T) {
    // Load historical data
    prices := loadTestData("BTC-USD", "2015-01-01", "2025-01-01")
    
    // Split into 5 windows
    windows := splitWalkForward(prices, 5)
    
    results := make([]BacktestResult, 0, len(windows))
    for _, w := range windows {
        result := runBacktest(w.Train, w.Test, defaultConfig)
        results = append(results, result)
    }
    
    // Validate consistency
    sharpeStd := stdDev(mapToSharpe(results))
    assert.Less(t, sharpeStd, 0.5, "Sharpe should be consistent across windows")
    
    // Validate average performance
    avgSharpe := mean(mapToSharpe(results))
    assert.Greater(t, avgSharpe, 1.0, "Average Sharpe should be > 1.0")
}
```

### 4.2 Bootstrap Validation

```python
def test_bootstrap_ci_coverage():
    """Bootstrap CI should contain true mean 95% of time."""
    np.random.seed(42)
    
    # Known distribution
    true_mean = 100
    coverage_count = 0
    
    for _ in range(100):
        # Sample from known distribution
        sample = np.random.normal(true_mean, 10, 100)
        
        # Calculate CI
        ci_lower, ci_upper = bootstrap_ci(sample, iterations=1000)
        
        # Check if true mean is in CI
        if ci_lower <= true_mean <= ci_upper:
            coverage_count += 1
    
    # Should be ~95%
    coverage = coverage_count / 100
    assert 0.90 <= coverage <= 0.99
```

---

## 5. CHAOS ENGINEERING TESTS

### 5.1 Service Failure

```go
func TestChaos_PythonServiceFailure(t *testing.T) {
    // Start service with mock Python that fails
    svc := setupServiceWithMockPython(func() {
        panic("simulated failure")
    })
    
    // Should use cached data
    result, err := svc.GetQSpectrum(context.Background(), "BTC-USD")
    
    // Should degrade gracefully, not error
    assert.NoError(t, err)
    assert.True(t, result.IsCached)
    assert.True(t, result.IsPartial)
}
```

### 5.2 Database Latency

```go
func TestChaos_DatabaseLatency(t *testing.T) {
    // Inject latency
    svc := setupServiceWithLatentDB(5 * time.Second)
    
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()
    
    // Should timeout gracefully
    result, err := svc.GetMarketData(ctx, "BTC-USD")
    
    assert.Error(t, err)
    assert.Equal(t, ErrTimeout, err)
    assert.Nil(t, result)
}
```

---

## 6. PERFORMANCE TESTS

### 6.1 Load Testing (k6)

```javascript
// tests/load/api_load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '1m', target: 10 },   // Ramp up
        { duration: '3m', target: 50 },   // Plateau
        { duration: '1m', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<200'], // 95% < 200ms
        http_req_failed: ['rate<0.01'],   // < 1% errors
    },
};

const BASE_URL = 'http://localhost:8080/api/v1';

export default function() {
    // Get market data
    const res = http.get(`${BASE_URL}/market/history?symbol=BTC-USD&timeframe=1d`);
    
    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 200ms': (r) => r.timings.duration < 200,
        'has data': (r) => JSON.parse(r.body).data.points.length > 0,
    });
    
    sleep(1);
}
```

### 6.2 Benchmarks Summary

| Operation | Target | Max |
|-----------|--------|-----|
| Annual Cycle | < 200ms | 500ms |
| QSpectrum | < 500ms | 1s |
| Composite Line | < 100ms | 300ms |
| Bootstrap (1000 iter) | < 5s | 10s |
| Market Data Import | < 60s | 120s |

---

## 7. TEST COMMANDS

```bash
# Go tests
make test                    # All unit tests
make test-integration        # Integration tests
make test-race              # Race detection
make test-coverage          # Generate coverage report
make bench                  # Run benchmarks

# Python tests
cd quant && pytest          # All tests
pytest --cov=qspectrum      # Coverage
pytest -m "not slow"        # Skip slow tests
pytest --hypothesis-seed=42 # Property tests

# Load tests
k6 run tests/load/api_load.js

# Chaos tests
make chaos-test
```

---

## 8. CI/CD TEST PIPELINE

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: make test
      - run: make test-coverage
      - uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - run: make test-integration

  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: cd quant && pip install -r requirements.txt
      - run: cd quant && pytest --cov
```

---

**Версия документации:** 3.2 Final
