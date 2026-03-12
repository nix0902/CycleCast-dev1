import { NextRequest, NextResponse } from 'next/server'
import { analyzeSeasonality, calculateBootstrapCI } from '@/lib/quant'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { prices, config } = body
    
    // Validate input
    if (!prices || !Array.isArray(prices) || prices.length < 252) {
      return NextResponse.json(
        { success: false, error: 'Insufficient price data (minimum 252 trading days required for annual analysis)' },
        { status: 400 }
      )
    }
    
    // Run seasonality analysis
    const result = await analyzeSeasonality(prices, config)
    
    // Calculate bootstrap CI for FTE correlation
    const bootstrapResult = await calculateBootstrapCI(
      prices.map((p: number, i: number) => i > 0 ? (prices[i] - prices[i-1]) / prices[i-1] : 0).slice(1),
      { iterations: 500, confidenceLevel: 0.95 }
    )
    
    return NextResponse.json({
      success: true,
      data: {
        ...result,
        bootstrapCI: bootstrapResult,
      },
      metadata: {
        dataPoints: prices.length,
        yearsOfData: Math.floor(prices.length / 252),
        analyzedAt: new Date().toISOString(),
      },
    })
  } catch (error) {
    console.error('Seasonality analysis failed:', error)
    return NextResponse.json(
      { success: false, error: 'Seasonality analysis failed', details: String(error) },
      { status: 500 }
    )
  }
}
