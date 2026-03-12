import { NextRequest, NextResponse } from 'next/server'
import { analyzeQSpectrum } from '@/lib/quant'
import { db } from '@/lib/db'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { instrumentId, prices, config } = body
    
    // Validate input
    if (!prices || !Array.isArray(prices) || prices.length < 50) {
      return NextResponse.json(
        { success: false, error: 'Insufficient price data (minimum 50 points required)' },
        { status: 400 }
      )
    }
    
    // Run QSpectrum analysis
    const result = await analyzeQSpectrum(prices, config)
    
    // Store cycles in database if instrumentId provided
    if (instrumentId) {
      for (const cycle of result.cycles.slice(0, 5)) {
        await db.cycle.upsert({
          where: {
            instrumentId_timeframe_period: {
              instrumentId,
              timeframe: '1d',
              period: cycle.period,
            },
          },
          update: {
            energy: cycle.energy,
            stability: cycle.stability,
            correlation: cycle.correlation,
          },
          create: {
            instrumentId,
            timeframe: '1d',
            period: cycle.period,
            energy: cycle.energy,
            stability: cycle.stability,
            correlation: cycle.correlation,
          },
        })
      }
    }
    
    return NextResponse.json({
      success: true,
      data: result,
      metadata: {
        dataPoints: prices.length,
        analyzedAt: new Date().toISOString(),
      },
    })
  } catch (error) {
    console.error('QSpectrum analysis failed:', error)
    return NextResponse.json(
      { success: false, error: 'QSpectrum analysis failed', details: String(error) },
      { status: 500 }
    )
  }
}
