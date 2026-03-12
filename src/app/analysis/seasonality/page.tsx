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
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Calendar,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
  LineChart,
  Info
} from "lucide-react"

// FTE Status colors
const fteStatusColors = {
  VALID: "bg-green-500",
  INVALID: "bg-red-500",
  BROKEN: "bg-orange-500",
  INSUFFICIENT_DATA: "bg-gray-500"
}

// Regime colors
const regimeColors = {
  LOW_VOL: "bg-green-500/20 text-green-700 border-green-500",
  NORMAL_VOL: "bg-blue-500/20 text-blue-700 border-blue-500",
  HIGH_VOL: "bg-yellow-500/20 text-yellow-700 border-yellow-500",
  EXTREME_VOL: "bg-red-500/20 text-red-700 border-red-500"
}

// Monthly seasonality data (simulated)
const monthlyData = [
  { month: "Jan", avg: 0.012, win: 0.62, trades: 45 },
  { month: "Feb", avg: 0.008, win: 0.58, trades: 42 },
  { month: "Mar", avg: 0.015, win: 0.65, trades: 48 },
  { month: "Apr", avg: 0.022, win: 0.71, trades: 50 },
  { month: "May", avg: -0.005, win: 0.45, trades: 47 },
  { month: "Jun", avg: -0.012, win: 0.42, trades: 44 },
  { month: "Jul", avg: 0.018, win: 0.68, trades: 46 },
  { month: "Aug", avg: -0.008, win: 0.48, trades: 49 },
  { month: "Sep", avg: -0.025, win: 0.38, trades: 45 },
  { month: "Oct", avg: 0.005, win: 0.55, trades: 48 },
  { month: "Nov", avg: 0.028, win: 0.74, trades: 46 },
  { month: "Dec", avg: 0.015, win: 0.67, trades: 44 },
]

// Daily seasonal pattern
const dailyPattern = Array.from({ length: 252 }, (_, i) => ({
  day: i + 1,
  value: Math.sin(i * 2 * Math.PI / 252) * 0.3 + Math.random() * 0.1,
  confidence: 0.5 + Math.random() * 0.4
}))

export default function SeasonalityPage() {
  const [instrument, setInstrument] = useState("SPY")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [fteStatus, setFteStatus] = useState<"VALID" | "INVALID" | "BROKEN" | "INSUFFICIENT_DATA">("VALID")
  const [regime, setRegime] = useState<"LOW_VOL" | "NORMAL_VOL" | "HIGH_VOL" | "EXTREME_VOL">("NORMAL_VOL")
  const [fteCorrelation, setFteCorrelation] = useState(0.72)
  const [adaptiveThreshold, setAdaptiveThreshold] = useState(0.058)

  const instruments = [
    { symbol: "SPY", name: "S&P 500 ETF", type: "ETF", years: 30 },
    { symbol: "GLD", name: "Gold ETF", type: "ETF", years: 20 },
    { symbol: "BTC-USD", name: "Bitcoin", type: "CRYPTO", years: 10 },
    { symbol: "GBTC", name: "Grayscale Bitcoin Trust", type: "TRUST", years: 8 },
    { symbol: "GC=F", name: "Gold Futures", type: "FUTURES", years: 50 },
  ]

  const selectedInstrument = instruments.find(i => i.symbol === instrument)

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    // Simulate analysis
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Random results for demo
    const statuses = ["VALID", "INVALID", "BROKEN", "INSUFFICIENT_DATA"] as const
    const regimes = ["LOW_VOL", "NORMAL_VOL", "HIGH_VOL", "EXTREME_VOL"] as const
    
    setFteStatus(statuses[Math.floor(Math.random() * 2)]) // Mostly VALID/INVALID
    setRegime(regimes[Math.floor(Math.random() * 4)])
    setFteCorrelation(0.3 + Math.random() * 0.6)
    setAdaptiveThreshold(0.04 + Math.random() * 0.08)
    
    setIsAnalyzing(false)
  }

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Seasonality Analysis</h1>
          <p className="text-muted-foreground mt-1">
            Annual Cycle с адаптивным FTE порогом по методологии Ларри Вильямса
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={instrument} onValueChange={setInstrument}>
            <SelectTrigger className="w-[220px]">
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
                <Activity className="h-4 w-4 mr-2" />
                Run Analysis
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">FTE Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${fteStatusColors[fteStatus]}`} />
              <span className="text-2xl font-bold">{fteStatus}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {fteStatus === "VALID" ? "Seasonality pattern confirmed" : "Pattern validation failed"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">FTE Correlation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fteCorrelation.toFixed(3)}</div>
            <Progress value={fteCorrelation * 100} className="h-2 mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              Threshold: {adaptiveThreshold.toFixed(3)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Volatility Regime</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline" className={regimeColors[regime]}>
              {regime.replace("_", " ")}
            </Badge>
            <p className="text-xs text-muted-foreground mt-2">
              {regime === "LOW_VOL" && "Stricter threshold applied"}
              {regime === "NORMAL_VOL" && "Standard threshold"}
              {regime === "HIGH_VOL" && "Relaxed threshold × 1.2"}
              {regime === "EXTREME_VOL" && "Relaxed threshold × 1.5"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Years of Data</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedInstrument?.years || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {selectedInstrument?.type} instrument
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="annual" className="space-y-6">
        <TabsList>
          <TabsTrigger value="annual">Annual Cycle</TabsTrigger>
          <TabsTrigger value="monthly">Monthly Breakdown</TabsTrigger>
          <TabsTrigger value="decennial">Decennial Pattern</TabsTrigger>
          <TabsTrigger value="validation">FTE Validation</TabsTrigger>
        </TabsList>

        <TabsContent value="annual" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Seasonal Pattern Chart */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LineChart className="h-5 w-5" />
                  Annual Seasonal Pattern
                </CardTitle>
                <CardDescription>
                  Normalized seasonal tendency over 252 trading days
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px] flex items-end gap-0.5 overflow-x-auto pb-4">
                  {dailyPattern.map((d, i) => (
                    <div
                      key={i}
                      className="flex-shrink-0 w-1 bg-primary/80 rounded-t transition-all hover:bg-primary"
                      style={{
                        height: `${Math.abs(d.value) * 200 + 20}px`,
                        backgroundColor: d.value > 0 ? 'hsl(142, 76%, 36%)' : 'hsl(0, 84%, 60%)'
                      }}
                      title={`Day ${d.day}: ${d.value.toFixed(3)}`}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>Jan</span>
                  <span>Apr</span>
                  <span>Jul</span>
                  <span>Oct</span>
                  <span>Dec</span>
                </div>
              </CardContent>
            </Card>

            {/* Best/Worst Months */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                  Best Months
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {monthlyData
                  .sort((a, b) => b.avg - a.avg)
                  .slice(0, 3)
                  .map((m, i) => (
                    <div key={m.month} className="flex items-center justify-between p-2 rounded-lg bg-green-500/10">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-green-500/20">
                          #{i + 1}
                        </Badge>
                        <span className="font-medium">{m.month}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-green-600 font-medium">
                          +{(m.avg * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Win: {(m.win * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingDown className="h-5 w-5 text-red-500" />
                  Worst Months
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {monthlyData
                  .sort((a, b) => a.avg - b.avg)
                  .slice(0, 3)
                  .map((m, i) => (
                    <div key={m.month} className="flex items-center justify-between p-2 rounded-lg bg-red-500/10">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-red-500/20">
                          #{i + 1}
                        </Badge>
                        <span className="font-medium">{m.month}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-red-600 font-medium">
                          {(m.avg * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Win: {(m.win * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="monthly" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Monthly Performance Breakdown</CardTitle>
              <CardDescription>
                Average returns and win rates by calendar month
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
                {monthlyData.map((m) => (
                  <div 
                    key={m.month} 
                    className={`p-4 rounded-lg border ${
                      m.avg > 0 ? 'border-green-500/50 bg-green-500/5' : 'border-red-500/50 bg-red-500/5'
                    }`}
                  >
                    <div className="font-semibold text-lg">{m.month}</div>
                    <div className={`text-2xl font-bold ${m.avg > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {m.avg > 0 ? '+' : ''}{(m.avg * 100).toFixed(1)}%
                    </div>
                    <Separator className="my-2" />
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Win</span>
                        <div className="font-medium">{(m.win * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Trades</span>
                        <div className="font-medium">{m.trades}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="decennial" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Decennial Pattern (Year Digit 0-9)
              </CardTitle>
              <CardDescription>
                Performance by year digit (year % 10) — identifies multi-year cycles
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-5">
                {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => {
                  const avgReturn = (Math.random() * 0.06 - 0.02)
                  const isPositive = avgReturn > 0
                  return (
                    <div 
                      key={digit}
                      className={`p-4 rounded-lg border text-center ${
                        isPositive ? 'border-green-500/50 bg-green-500/5' : 'border-red-500/50 bg-red-500/5'
                      }`}
                    >
                      <div className="text-3xl font-bold">{digit}</div>
                      <div className="text-xs text-muted-foreground mb-2">
                        Years ending in {digit}
                      </div>
                      <div className={`font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                        {isPositive ? '+' : ''}{(avgReturn * 100).toFixed(1)}%
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-4 p-3 rounded-lg bg-muted/50 flex items-start gap-2">
                <Info className="h-4 w-4 mt-0.5 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  <strong>Decennial Pattern:</strong> Ларри Вильямс заметил, что определенные годы 
                  (например, года заканчивающиеся на 2, 5, 8) имеют тенденцию показывать схожее поведение. 
                  Это связано с 10-летним циклом экономической активности.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="validation" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                FTE Validation Results
              </CardTitle>
              <CardDescription>
                Forecast Theoretical Efficiency validation per TZ.md §2.3
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Validation Checklist */}
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span>Correlation &gt; Adaptive Threshold</span>
                  </div>
                  <Badge variant="outline" className="bg-green-500/20 text-green-700">
                    PASS ({fteCorrelation.toFixed(3)} &gt; {adaptiveThreshold.toFixed(3)})
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span>Rolling Window Stability</span>
                  </div>
                  <Badge variant="outline" className="bg-green-500/20 text-green-700">
                    PASS (72% windows positive)
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span>Broken Seasonality Detection</span>
                  </div>
                  <Badge variant="outline" className="bg-green-500/20 text-green-700">
                    PASS (no broken periods)
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span>Direction Accuracy</span>
                  </div>
                  <Badge variant="outline" className="bg-green-500/20 text-green-700">
                    PASS (58% accuracy)
                  </Badge>
                </div>
              </div>

              <Separator />

              {/* Adaptive Threshold Formula */}
              <div className="p-4 rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">Adaptive Threshold Formula (TZ.md §2.3.2)</h4>
                <code className="text-sm">
                  threshold = base × (1 + λ × (current_vol / long_term_vol - 1))
                </code>
                <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Base:</span>
                    <span className="font-medium ml-2">
                      {instrument.includes("BTC") ? "0.08" : "0.05"}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">λ (sensitivity):</span>
                    <span className="font-medium ml-2">0.5</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Floor:</span>
                    <span className="font-medium ml-2">50% of base</span>
                  </div>
                </div>
              </div>

              {/* Walk-Forward Results */}
              <div>
                <h4 className="font-medium mb-3">Walk-Forward Validation (12 periods)</h4>
                <div className="grid gap-2 grid-cols-6">
                  {Array.from({ length: 12 }, (_, i) => {
                    const passed = Math.random() > 0.2
                    return (
                      <div 
                        key={i}
                        className={`p-2 rounded text-center text-sm ${
                          passed ? 'bg-green-500/20 text-green-700' : 'bg-red-500/20 text-red-700'
                        }`}
                      >
                        <div className="font-medium">P{i + 1}</div>
                        <div className="text-xs">{passed ? 'PASS' : 'FAIL'}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
