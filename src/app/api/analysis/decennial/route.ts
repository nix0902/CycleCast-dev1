import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { spawn } from 'child_process'
import path from 'path'

interface DecennialRequest {
  instrumentId: string
  currentYear?: number
  instrumentType?: 'tradfi' | 'crypto'
}

interface DigitStats {
  digit: number
  years: number[]
  avgReturn: number
  stdReturn: number
  winRate: number
  normalizedScore: number
  sampleCount: number
  confidence: number
}

interface DecennialResult {
  status: 'valid' | 'insufficient_data' | 'crypto_unsupported' | 'error'
  digitStats: Record<number, DigitStats>
  currentDigit: number
  currentYear: number
  mostSimilarDigit: number | null
  similarityScore: number
  projectedTrend: 'bullish' | 'bearish' | 'neutral' | null
  message: string
  yearsAnalyzed: number
  dataCompleteness: number
}

export async function POST(request: NextRequest) {
  try {
    const body: DecennialRequest = await request.json()
    const { instrumentId, currentYear, instrumentType = 'tradfi' } = body

    if (!instrumentId) {
      return NextResponse.json(
        { error: 'instrumentId is required' },
        { status: 400 }
      )
    }

    // Get instrument info
    const instrument = await db.instrument.findUnique({
      where: { id: instrumentId }
    })

    if (!instrument) {
      return NextResponse.json(
        { error: 'Instrument not found' },
        { status: 404 }
      )
    }

    // Check if crypto (not enough history for decennial)
    const isCrypto = instrument.type === 'CRYPTO' || instrumentType === 'crypto'
    if (isCrypto) {
      return NextResponse.json({
        status: 'crypto_unsupported',
        digitStats: {},
        currentDigit: (currentYear || new Date().getFullYear()) % 10,
        currentYear: currentYear || new Date().getFullYear(),
        mostSimilarDigit: null,
        similarityScore: 0,
        projectedTrend: null,
        message: 'Decennial pattern not applicable for crypto (< 30 years of data)',
        yearsAnalyzed: 0,
        dataCompleteness: 0
      } as DecennialResult)
    }

    // Get historical data
    const marketData = await db.marketData.findMany({
      where: { instrumentId },
      orderBy: { timestamp: 'asc' }
    })

    if (marketData.length < 100) {
      return NextResponse.json({
        status: 'insufficient_data',
        digitStats: {},
        currentDigit: (currentYear || new Date().getFullYear()) % 10,
        currentYear: currentYear || new Date().getFullYear(),
        mostSimilarDigit: null,
        similarityScore: 0,
        projectedTrend: null,
        message: 'Insufficient data for decennial analysis',
        yearsAnalyzed: marketData.length,
        dataCompleteness: 0
      } as DecennialResult)
    }

    // Extract prices and years
    const years = marketData.map(d => new Date(d.timestamp).getFullYear())
    const prices = marketData.map(d => d.close.toNumber())

    // Call Python analysis
    const result = await runPythonDecennial(prices, years, currentYear, instrumentType)

    return NextResponse.json(result)

  } catch (error) {
    console.error('Decennial analysis error:', error)
    return NextResponse.json(
      { error: 'Analysis failed', details: String(error) },
      { status: 500 }
    )
  }
}

async function runPythonDecennial(
  prices: number[],
  years: number[],
  currentYear?: number,
  instrumentType: string = 'tradfi'
): Promise<DecennialResult> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(process.cwd(), 'quant', 'cli', 'decennial_cli.py')
    
    const input = JSON.stringify({
      prices,
      years,
      current_year: currentYear || new Date().getFullYear(),
      instrument_type: instrumentType
    })

    const python = spawn('python', [scriptPath], {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    })

    let output = ''
    let errorOutput = ''

    python.stdin.write(input)
    python.stdin.end()

    python.stdout.on('data', (data) => {
      output += data.toString()
    })

    python.stderr.on('data', (data) => {
      errorOutput += data.toString()
    })

    python.on('close', (code) => {
      if (code !== 0) {
        console.error('Python error:', errorOutput)
        reject(new Error(errorOutput || 'Python script failed'))
        return
      }

      try {
        const result = JSON.parse(output)
        resolve(transformResult(result))
      } catch (e) {
        reject(new Error('Failed to parse Python output'))
      }
    })

    python.on('error', (err) => {
      reject(err)
    })
  })
}

function transformResult(pyResult: any): DecennialResult {
  const digitStats: Record<number, DigitStats> = {}
  
  for (const [digit, stats] of Object.entries(pyResult.digit_stats || {})) {
    const s = stats as any
    digitStats[parseInt(digit)] = {
      digit: parseInt(digit),
      years: s.years || [],
      avgReturn: s.avg_return || 0,
      stdReturn: s.std_return || 0,
      winRate: s.win_rate || 0,
      normalizedScore: s.normalized_score || 0.5,
      sampleCount: s.sample_count || 0,
      confidence: s.confidence || 0
    }
  }

  return {
    status: pyResult.status || 'valid',
    digitStats,
    currentDigit: pyResult.current_digit || 0,
    currentYear: pyResult.current_year || new Date().getFullYear(),
    mostSimilarDigit: pyResult.most_similar_digit,
    similarityScore: pyResult.similarity_score || 0,
    projectedTrend: pyResult.projected_trend,
    message: pyResult.message || '',
    yearsAnalyzed: pyResult.years_analyzed || 0,
    dataCompleteness: pyResult.data_completeness || 0
  }
}
