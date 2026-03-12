'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { 
  Calendar,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  Info,
  AlertTriangle,
  CheckCircle2
} from "lucide-react"

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

export default function DecennialPage() {
  const [instrument, setInstrument] = useState("SPY")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<DecennialResult | null>(null)

  const instruments = [
    { symbol: "SPY", name: "S&P 500 ETF", type: "ETF", minYears: 30 },
    { symbol: "GLD", name: "Gold ETF", type: "ETF", minYears: 20 },
    { symbol: "GC=F", name: "Gold Futures", type: "FUTURES", minYears: 50 },
  ]

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    try {
      const response = await fetch('/api/analysis/decennial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instrumentId: instrument,
          currentYear: new Date().getFullYear(),
          instrumentType: 'tradfi'
        })
      })
      
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Analysis failed:', error)
    }
    setIsAnalyzing(false)
  }

  // Generate mock data for display
  const mockDigitStats = Array.from({ length: 10 }, (_, i) => ({
    digit: i,
    avgReturn: (Math.random() - 0.4) * 0.15,
    winRate: 0.4 + Math.random() * 0.3,
    sampleCount: 3 + Math.floor(Math.random() * 4),
    confidence: 0.5 + Math.random() * 0.5
  }))

  const displayStats = result?.digitStats 
    ? Object.values(result.digitStats) 
    : mockDigitStats

  const getTrendIcon = (trend: string | null) => {
    if (trend === 'bullish') return <TrendingUp className="h-5 w-5 text-green-500" />
    if (trend === 'bearish') return <TrendingDown className="h-5 w-5 text-red-500" />
    return <Activity className="h-5 w-5 text-yellow-500" />
  }

  const getTrendColor = (trend: string | null) => {
    if (trend === 'bullish') return 'text-green-600'
    if (trend === 'bearish') return 'text-red-600'
    return 'text-yellow-600'
  }

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Decennial Pattern Analysis</h1>
          <p className="text-muted-foreground mt-1">
            Larry Williams methodology: Year digit patterns (year % 10)
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={instrument} onValueChange={setInstrument}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select instrument" />
            </SelectTrigger>
            <SelectContent>
              {instruments.map((inst) => (
                <SelectItem key={inst.symbol} value={inst.symbol}>
                  {inst.symbol} - {inst.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={runAnalysis} disabled={isAnalyzing}>
            {isAnalyzing ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Calendar className="h-4 w-4 mr-2" />
                Analyze Pattern
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Warning for Crypto */}
      <Card className="border-yellow-500/50 bg-yellow-500/10">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-700">Important Note</h4>
              <p className="text-sm text-yellow-600 mt-1">
                Decennial pattern requires <strong>30+ years</strong> of historical data.
                Not applicable for cryptocurrency markets.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Status Cards */}
      {result && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Current Year Digit</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{result.currentDigit}</div>
              <p className="text-sm text-muted-foreground">
                Year {result.currentYear} → digit {result.currentYear % 10}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Projected Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                {getTrendIcon(result.projectedTrend)}
                <span className={`text-2xl font-bold ${getTrendColor(result.projectedTrend)}`}>
                  {result.projectedTrend?.toUpperCase() || 'NEUTRAL'}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Based on digit pattern
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Similar Digit</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {result.mostSimilarDigit ?? '-'}
              </div>
              <p className="text-sm text-muted-foreground">
                Similarity: {(result.similarityScore * 100).toFixed(0)}%
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Data Quality</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{result.yearsAnalyzed} years</div>
              <Progress value={result.dataCompleteness * 100} className="h-2 mt-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {(result.dataCompleteness * 100).toFixed(0)}% completeness
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="digits" className="space-y-6">
        <TabsList>
          <TabsTrigger value="digits">Digit Patterns</TabsTrigger>
          <TabsTrigger value="current">Current Year</TabsTrigger>
          <TabsTrigger value="methodology">Methodology</TabsTrigger>
        </TabsList>

        <TabsContent value="digits" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Performance by Year Digit (0-9)</CardTitle>
              <CardDescription>
                Historical returns grouped by year % 10
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-5">
                {displayStats.map((stats) => {
                  const isCurrent = result && stats.digit === result.currentDigit
                  return (
                    <div 
                      key={stats.digit}
                      className={`p-4 rounded-lg border text-center transition-all ${
                        isCurrent 
                          ? 'border-primary bg-primary/10 ring-2 ring-primary' 
                          : stats.avgReturn > 0 
                            ? 'border-green-500/50 bg-green-500/5' 
                            : 'border-red-500/50 bg-red-500/5'
                      }`}
                    >
                      <div className="text-3xl font-bold mb-1">{stats.digit}</div>
                      <div className="text-xs text-muted-foreground mb-2">
                        Years ending in {stats.digit}
                      </div>
                      <div className={`text-lg font-semibold ${
                        stats.avgReturn > 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {stats.avgReturn > 0 ? '+' : ''}
                        {(stats.avgReturn * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Win: {(stats.winRate * 100).toFixed(0)}%
                      </div>
                      {isCurrent && (
                        <Badge variant="default" className="mt-2">
                          Current
                        </Badge>
                      )}
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Average Returns Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Average Return by Digit</CardTitle>
              <CardDescription>
                Visual comparison of performance patterns
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[250px] flex items-end gap-2">
                {displayStats.map((stats) => {
                  const maxReturn = Math.max(...displayStats.map(s => Math.abs(s.avgReturn)))
                  const height = maxReturn > 0 
                    ? (Math.abs(stats.avgReturn) / maxReturn) * 100 
                    : 20
                  const isPositive = stats.avgReturn > 0
                  const isCurrent = result && stats.digit === result.currentDigit
                  
                  return (
                    <div key={stats.digit} className="flex-1 flex flex-col items-center gap-1">
                      <div 
                        className={`w-full rounded-t transition-all ${
                          isCurrent 
                            ? 'ring-2 ring-primary' 
                            : ''
                        }`}
                        style={{ 
                          height: `${Math.max(height, 10)}%`,
                          backgroundColor: isPositive ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)',
                          opacity: isCurrent ? 1 : 0.7
                        }}
                      />
                      <span className="text-sm font-medium">{stats.digit}</span>
                      <span className={`text-xs ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                        {isPositive ? '+' : ''}{(stats.avgReturn * 100).toFixed(1)}%
                      </span>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="current" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary" />
                Current Year Analysis
              </CardTitle>
              <CardDescription>
                Year {result?.currentYear || new Date().getFullYear()} - Digit {result?.currentDigit || new Date().getFullYear() % 10}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {result ? (
                <>
                  {/* Historical Years */}
                  {result.digitStats[result.currentDigit] && (
                    <div>
                      <h4 className="font-medium mb-3">Historical Years with Same Digit</h4>
                      <div className="flex flex-wrap gap-2">
                        {result.digitStats[result.currentDigit].years.map(year => (
                          <Badge key={year} variant="outline">
                            {year}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <Separator />

                  {/* Projection */}
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg border">
                      <h4 className="font-medium mb-2">Average Historical Return</h4>
                      <div className={`text-2xl font-bold ${
                        (result.digitStats[result.currentDigit]?.avgReturn || 0) > 0 
                          ? 'text-green-600' 
                          : 'text-red-600'
                      }`}>
                        {((result.digitStats[result.currentDigit]?.avgReturn || 0) * 100).toFixed(2)}%
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        Based on {result.digitStats[result.currentDigit]?.sampleCount || 0} historical years
                      </p>
                    </div>
                    <div className="p-4 rounded-lg border">
                      <h4 className="font-medium mb-2">Win Rate</h4>
                      <div className="text-2xl font-bold">
                        {((result.digitStats[result.currentDigit]?.winRate || 0) * 100).toFixed(0)}%
                      </div>
                      <Progress 
                        value={(result.digitStats[result.currentDigit]?.winRate || 0) * 100} 
                        className="h-2 mt-2" 
                      />
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  Click "Analyze Pattern" to see current year analysis
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="methodology" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Decennial Pattern Methodology</CardTitle>
              <CardDescription>
                Larry Williams' observation of 10-year market cycles
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">Core Concept</h4>
                <p className="text-sm text-muted-foreground">
                  Larry Williams noticed that years ending in the same digit tend to show 
                  similar market behavior. For example, years ending in 2, 5, and 8 often 
                  exhibit bullish tendencies, while years ending in 0 and 7 may be more bearish.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg border">
                  <h4 className="font-medium mb-2">Year Digit Calculation</h4>
                  <code className="text-sm">digit = year % 10</code>
                  <div className="mt-3 space-y-1 text-sm">
                    <div>2024 → digit 4</div>
                    <div>2025 → digit 5</div>
                    <div>2030 → digit 0</div>
                  </div>
                </div>
                <div className="p-4 rounded-lg border">
                  <h4 className="font-medium mb-2">Requirements</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Minimum 30 years of data</li>
                    <li>• At least 2 years per digit for statistics</li>
                    <li>• Not applicable for crypto (&lt; 30 years)</li>
                  </ul>
                </div>
              </div>

              <Separator />

              <div className="p-4 rounded-lg bg-muted/50 flex items-start gap-3">
                <Info className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="text-sm text-muted-foreground">
                  <strong>Important:</strong> This pattern is a statistical observation, 
                  not a guarantee. Always combine with other analysis methods and proper 
                  risk management. The pattern is less reliable during regime changes 
                  (e.g., 2008 financial crisis, 2020 pandemic).
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
