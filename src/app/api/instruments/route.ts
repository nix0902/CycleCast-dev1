import { NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET() {
  try {
    const instruments = await db.instrument.findMany({
      where: { isActive: true },
      orderBy: { symbol: 'asc' },
    })
    
    return NextResponse.json({
      success: true,
      data: instruments,
      count: instruments.length,
    })
  } catch (error) {
    console.error('Failed to fetch instruments:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch instruments' },
      { status: 500 }
    )
  }
}
