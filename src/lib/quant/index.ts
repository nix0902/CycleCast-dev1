/**
 * CycleCast Quant Module Integration
 * 
 * Provides Node.js wrappers for Python quant modules:
 * - QSpectrum: Cycle detection using Burg's MEM
 * - Phenom: DTW-based historical analogy search
 * - Bootstrap: Confidence interval calculation
 * - Seasonality: FTE validation, regime detection
 */

import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'

const execAsync = promisify(exec)

const PROJECT_ROOT = process.cwd()
const QUANT_PATH = path.join(PROJECT_ROOT, 'quant')

export interface QSpectrumResult {
  cycles: Array<{
    period: number
    energy: number
    stability: number
    correlation: number
    phase?: number
    amplitude?: number
  }>
  top3: Array<{
    period: number
    energy: number
    stability: number
  }>
  dominantPeriod: number
  spectralEntropy: number
}

export interface SeasonalityResult {
  cycleData: Array<{
    day: number
    value: number
    confidence: number
  }>
  fteCorrelation: number
  fteIsValid: boolean
  regimeType: string
  adaptiveThreshold: number
}

export interface BacktestResult {
  totalReturn: number
  sharpeRatio: number
  maxDrawdown: number
  winRate: number
  pValue: number
  bootstrapCiLower: number
  bootstrapCiUpper: number
}

/**
 * Execute Python script and parse JSON result
 */
async function runPythonScript(
  module: string,
  functionName: string,
  args: Record<string, unknown>
): Promise<unknown> {
  const argsJson = JSON.stringify(args).replace(/'/g, "'\\''")
  const script = `
import json
import sys
sys.path.insert(0, '${QUANT_PATH}')
from ${module} import ${functionName}

args = json.loads('${argsJson}')
result = ${functionName}(**args)
print(json.dumps(result))
`

  try {
    const { stdout, stderr } = await execAsync(`python3 -c "${script}"`, {
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer for large results
    })
    
    if (stderr && !stderr.includes('Warning')) {
      console.error('Python stderr:', stderr)
    }
    
    return JSON.parse(stdout)
  } catch (error) {
    console.error('Python execution error:', error)
    throw new Error(`Python script failed: ${error}`)
  }
}

/**
 * QSpectrum Analysis
 * Detects dominant cycles using cyclic correlation and Burg's MEM
 */
export async function analyzeQSpectrum(
  prices: number[],
  config?: {
    minPeriod?: number
    maxPeriod?: number
    normalization?: string
  }
): Promise<QSpectrumResult> {
  const result = await runPythonScript('qspectrum.core', 'qspectrum', {
    prices,
    config: config || {
      min_period: 10,
      max_period: 200,
      normalization: 'zscore',
    },
  }) as QSpectrumResult
  
  return result
}

/**
 * Seasonality Analysis with FTE Validation
 */
export async function analyzeSeasonality(
  prices: number[],
  config?: {
    baseThreshold?: number
    sensitivityLambda?: number
    rollingWindow?: number
  }
): Promise<SeasonalityResult> {
  // Combine seasonality and FTE validation
  const fteResult = await runPythonScript('seasonality.fte', 'validate_fte', {
    prices,
    config: config || {
      base_threshold: 0.08,
      sensitivity_lambda: 0.5,
      rolling_window: 21,
    },
  })
  
  const regimeResult = await runPythonScript('seasonality.regime', 'detect_regime', {
    prices,
  })
  
  return {
    cycleData: [], // Would be populated from annual cycle analysis
    fteCorrelation: (fteResult as Record<string, unknown>).pearson_correlation as number,
    fteIsValid: (fteResult as Record<string, unknown>).is_valid as boolean,
    regimeType: (regimeResult as Record<string, unknown>).regime_type as string,
    adaptiveThreshold: (fteResult as Record<string, unknown>).threshold_used as number,
  }
}

/**
 * Bootstrap Confidence Interval
 */
export async function calculateBootstrapCI(
  returns: number[],
  config?: {
    iterations?: number
    confidenceLevel?: number
    statistic?: string
  }
): Promise<{
  ciLower: number
  ciUpper: number
  mean: number
  std: number
}> {
  const result = await runPythonScript('bootstrap.core', 'bootstrap_ci', {
    data: returns,
    config: config || {
      iterations: 1000,
      confidence_level: 0.95,
      statistic: 'mean',
    },
  })
  
  return {
    ciLower: (result as Record<string, unknown>).ci_lower as number,
    ciUpper: (result as Record<string, unknown>).ci_upper as number,
    mean: (result as Record<string, unknown>).mean as number,
    std: (result as Record<string, unknown>).std as number,
  }
}

/**
 * Phenomenological Analysis (Historical Analogies)
 */
export async function findHistoricalAnalogies(
  targetPrices: number[],
  historyPrices: number[],
  config?: {
    correlationThreshold?: number
    maxCandidates?: number
    projectionHorizon?: number
  }
): Promise<{
  matches: Array<{
    distance: number
    correlation: number
    projection: number[]
  }>
  confidence: number
}> {
  const result = await runPythonScript('phenom.dtw', 'adaptive_dtw', {
    target: targetPrices,
    history: historyPrices,
    config: config || {
      correlation_threshold: 0.6,
      max_candidates: 100,
      projection_horizon: 30,
    },
  })
  
  return {
    matches: ((result as Record<string, unknown>).matches as Array<Record<string, unknown>>)?.map(m => ({
      distance: m.distance as number,
      correlation: m.correlation as number,
      projection: m.projection as number[],
    })) || [],
    confidence: (result as Record<string, unknown>).confidence as number,
  }
}

/**
 * Composite Line Generation
 */
export async function generateCompositeLine(
  prices: number[],
  cycles: Array<{ period: number; energy: number }>,
  forecastDays: number = 90
): Promise<{
  lineData: number[]
  resonancePoints: Array<{ index: number; type: string; strength: number }>
}> {
  const result = await runPythonScript('qspectrum.core', 'composite_line', {
    prices,
    cycles,
    forecast_days: forecastDays,
  })
  
  return {
    lineData: (result as Record<string, unknown>).line_data as number[],
    resonancePoints: (result as Record<string, unknown>).resonance_points as Array<{ index: number; type: string; strength: number }>,
  }
}
