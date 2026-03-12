'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { 
  Activity, 
  RefreshCw,
  WaveSine,
  BarChart3,
  LineChart,
  Info,
  TrendingUp,
  TrendingDown,
  Zap
} from "lucide-react"

// Spectrum data (simulated)
const spectrumData = Array.from({ length: 191 }, (_, i) => ({
  period: 10 + i,
  energy: Math.exp(-((i - 30) ** 2) / 2000) * 0.85 + 
           Math.exp(-((i - 70) ** 2) / 1000) * 0.72 +
           Math.exp(-((i - 140) ** 2) / 800) * 0.61 +
           Math.random() * 0.1,
  correlation: (Math.sin((i - 30) * 0.1) * 0.5 + 0.5) * 0.8 + Math.random() * 0.1,
  stability: 0.5 + Math.random() * 0.4
}))

// Top cycles
const topCycles = [
  { period: 14, energy: 0.85, stability: 0.72, phase: 0.25, amplitude: 0.12, direction: "up" as const },
  { period: 42, energy: 0.72, stability: 0.65, phase: 0.45, amplitude: 0.08, direction: "up" as const },
  { period: 98, energy: 0.61, stability: 0.58, phase: 0.72, amplitude: 0.05, direction: "down" as const },
  { period: 28, energy: 0.55, stability: 0.62, phase: 0.15, amplitude: 0.06, direction: "up" as const },
  { period: 56, energy: 0.48, stability: 0.55, phase: 0.88, amplitude: 0.04, direction: "down" as const },
]

// Composite line data
const compositeLine = Array.from({ length: 180 }, (_, i) => {
  const short = Math.sin(i * 2 * Math.PI / 14) * 0.3
  const medium = Math.sin(i * 2 * Math.PI / 42) * 0.4
  const long = Math.sin(i * 2 * Math.PI / 98) * 0.3
  return {
    day: i,
    value: short + medium + long,
    short,
    medium,
    long,
    resonance: Math.abs(short) > 0.2 && Math.abs(medium) > 0.2 && Math.abs(long) > 0.2
  }
})

// Resonance points
const resonancePoints = compositeLine
  .filter(d => d.resonance)
  .filter((_, i) => i % 10 === 0)
  .map(d => ({
    day: d.day,
    type: d.value > 0 ? "BUY" as const : "SELL" as const,
    strength: Math.abs(d.value)
  }))

export default function QSpectrumPage() {
  const [instrument, setInstrument] = useState("SPY")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [minPeriod, setMinPeriod] = useState([10])
  const [maxPeriod, setMaxPeriod] = useState([200])
  const [spectralEntropy, setSpectralEntropy] = useState(0.42)
  const [dominantPeriod, setDominantPeriod] = useState(14)

  const instruments = [
    { symbol: "SPY", name: "S&P 500 ETF", type: "ETF" },
    { symbol: "GLD", name: "Gold ETF", type: "ETF" },
    { symbol: "BTC-USD", name: "Bitcoin", type: "CRYPTO" },
    { symbol: "GBTC", name: "Grayscale Bitcoin Trust", type: "TRUST" },
    { symbol: "GC=F", name: "Gold Futures", type: "FUTURES" },
  ]

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    await new Promise(resolve => setTimeout(resolve, 2500))
    setSpectralEntropy(0.3 + Math.random() * 0.3)
    setDominantPeriod([14, 28, 42, 56][Math.floor(Math.random() * 4)])
    setIsAnalyzing(false)
  }

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">QSpectrum Analysis</h1>
          <p className="text-muted-foreground mt-1">
            Циклическая корреляция + МЭМ (Maximum Entropy Method)
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
                <Activity className="h-4 w-4 mr-2" />
                Analyze Cycles
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Dominant Period</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dominantPeriod} days</div>
            <p className="text-xs text-muted-foreground mt-1">
              Highest energy cycle
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Spectral Entropy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{spectralEntropy.toFixed(3)}</div>
            <Progress value={spectralEntropy * 100} className="h-2 mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              Lower = more cyclical
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Top 3 Resonance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">UP</div>
            <p className="text-xs text-muted-foreground mt-1">
              All 3 cycles aligned up
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Cycles Found</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground mt-1">
              Energy &gt; 0.4 threshold
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="spectrum" className="space-y-6">
        <TabsList>
          <TabsTrigger value="spectrum">Spectrum</TabsTrigger>
          <TabsTrigger value="cycles">Top Cycles</TabsTrigger>
          <TabsTrigger value="composite">Composite Line</TabsTrigger>
          <TabsTrigger value="resonance">Resonance Points</TabsTrigger>
        </TabsList>

        <TabsContent value="spectrum" className="space-y-6">
          {/* Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <Label>Min Period: {minPeriod[0]} days</Label>
                  <Slider
                    value={minPeriod}
                    onValueChange={setMinPeriod}
                    min={5}
                    max={50}
                    step={1}
                  />
                </div>
                <div className="space-y-4">
                  <Label>Max Period: {maxPeriod[0]} days</Label>
                  <Slider
                    value={maxPeriod}
                    onValueChange={setMaxPeriod}
                    min={50}
                    max={365}
                    step={1}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Spectrum Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Energy Spectrum
              </CardTitle>
              <CardDescription>
                Cycle energy by period — NOT FFT! Uses Burg&apos;s MEM for non-stationary data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] flex items-end gap-px overflow-x-auto pb-4">
                {spectrumData
                  .filter(d => d.period >= minPeriod[0] && d.period <= maxPeriod[0])
                  .map((d, i) => (
                    <div
                      key={d.period}
                      className="flex-shrink-0 w-2 bg-primary/80 rounded-t transition-all hover:bg-primary cursor-pointer"
                      style={{ height: `${d.energy * 250}px` }}
                      title={`Period: ${d.period}d, Energy: ${d.energy.toFixed(3)}, Stability: ${d.stability.toFixed(2)}`}
                    />
                  ))}
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>{minPeriod[0]}d</span>
                <span>Period (days)</span>
                <span>{maxPeriod[0]}d</span>
              </div>
            </CardContent>
          </Card>

          {/* Algorithm Info */}
          <Card className="bg-muted/50">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="space-y-2">
                  <h4 className="font-medium">Why NOT FFT?</h4>
                  <p className="text-sm text-muted-foreground">
                    QSpectrum разработан специально для нестационарных финансовых данных.
                    FFT предполагает стационарность и даёт артефакты на реальных рынках.
                  </p>
                  <div className="grid md:grid-cols-2 gap-4 mt-3">
                    <div className="p-3 rounded bg-background">
                      <h5 className="font-medium text-sm">Cyclic Correlation</h5>
                      <code className="text-xs">
                        C(p) = Σ P(t) × P(t-p) / (N - p)
                      </code>
                    </div>
                    <div className="p-3 rounded bg-background">
                      <h5 className="font-medium text-sm">Burg&apos;s MEM</h5>
                      <code className="text-xs">
                        P(f) = σ² / |1 + Σ aₖ × e^(-i2πfk)|²
                      </code>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="cycles" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Top 5 Dominant Cycles</CardTitle>
              <CardDescription>
                Ranked by energy with WFA stability
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {topCycles.map((cycle, i) => (
                  <div key={cycle.period} className="p-4 rounded-lg border">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Badge variant={i === 0 ? "default" : "secondary"} className="text-lg px-3">
                          #{i + 1}
                        </Badge>
                        <span className="text-2xl font-bold">{cycle.period} days</span>
                        <Badge 
                          variant="outline" 
                          className={cycle.direction === "up" ? "border-green-500 text-green-600" : "border-red-500 text-red-600"}
                        >
                          {cycle.direction === "up" ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                          {cycle.direction.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-muted-foreground">Energy</div>
                        <div className="text-xl font-bold">{(cycle.energy * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Stability</span>
                          <span>{(cycle.stability * 100).toFixed(0)}%</span>
                        </div>
                        <Progress value={cycle.stability * 100} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Phase</span>
                          <span>{(cycle.phase * 360).toFixed(0)}°</span>
                        </div>
                        <Progress value={cycle.phase * 100} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Amplitude</span>
                          <span>{(cycle.amplitude * 100).toFixed(1)}%</span>
                        </div>
                        <Progress value={cycle.amplitude * 500} className="h-2" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="composite" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="h-5 w-5" />
                Composite Line (3-Cycle Resonance)
              </CardTitle>
              <CardDescription>
                Ларри Вильямс накладывает три волны и ищет точки резонанса
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Composite Chart */}
              <div className="h-[300px] relative overflow-x-auto pb-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full h-px bg-border" />
                </div>
                <div className="h-full flex items-end gap-px">
                  {compositeLine.map((d, i) => (
                    <div
                      key={i}
                      className={`flex-shrink-0 w-1 rounded-t transition-all ${
                        d.value > 0 ? 'bg-green-500/80' : 'bg-red-500/80'
                      } ${d.resonance ? 'ring-2 ring-yellow-400' : ''}`}
                      style={{ 
                        height: `${Math.abs(d.value) * 200 + 20}px`,
                        marginTop: d.value > 0 ? 'auto' : '0',
                        marginBottom: d.value > 0 ? '0' : 'auto'
                      }}
                      title={`Day ${d.day}: ${(d.value * 100).toFixed(1)}%`}
                    />
                  ))}
                </div>
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>Day 0</span>
                <span>Forecast (90 days)</span>
                <span>Day 180</span>
              </div>

              <Separator className="my-6" />

              {/* Individual Cycles */}
              <h4 className="font-medium mb-4">Individual Cycle Components</h4>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg border bg-green-500/5">
                  <h5 className="font-medium mb-2">Short Cycle (14d)</h5>
                  <div className="text-3xl font-bold text-green-600">↑ UP</div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Currently bullish phase
                  </p>
                </div>
                <div className="p-4 rounded-lg border bg-green-500/5">
                  <h5 className="font-medium mb-2">Medium Cycle (42d)</h5>
                  <div className="text-3xl font-bold text-green-600">↑ UP</div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Rising toward peak
                  </p>
                </div>
                <div className="p-4 rounded-lg border bg-red-500/5">
                  <h5 className="font-medium mb-2">Long Cycle (98d)</h5>
                  <div className="text-3xl font-bold text-red-600">↓ DOWN</div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Declining phase
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="resonance" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-yellow-500" />
                Resonance Points
              </CardTitle>
              <CardDescription>
                Точки где все три цикла направлены в одну сторону — ключевой принцип Ларри Вильямса
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="p-4 rounded-lg bg-muted/50 mb-6">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <p className="text-sm text-muted-foreground">
                    <strong>Ключевой принцип:</strong> Ларри Вильямс не ищет один идеальный цикл. 
                    Он накладывает три волны разной длины и ищет точки &quot;резонанса&quot; — 
                    когда все три цикла направлены в одну сторону.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {resonancePoints.slice(0, 12).map((point, i) => (
                  <div 
                    key={i}
                    className={`p-4 rounded-lg border ${
                      point.type === "BUY" 
                        ? "border-green-500/50 bg-green-500/10" 
                        : "border-red-500/50 bg-red-500/10"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Badge 
                        variant="outline" 
                        className={point.type === "BUY" ? "border-green-500 text-green-600" : "border-red-500 text-red-600"}
                      >
                        {point.type === "BUY" ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                        {point.type}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        Day {point.day}
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-muted-foreground">Strength:</span>
                      <span className="font-medium ml-2">{(point.strength * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>

              <Separator className="my-6" />

              {/* Summary Stats */}
              <div className="grid md:grid-cols-3 gap-4">
                <div className="text-center p-4">
                  <div className="text-3xl font-bold text-green-600">
                    {resonancePoints.filter(p => p.type === "BUY").length}
                  </div>
                  <div className="text-sm text-muted-foreground">BUY Signals</div>
                </div>
                <div className="text-center p-4">
                  <div className="text-3xl font-bold text-red-600">
                    {resonancePoints.filter(p => p.type === "SELL").length}
                  </div>
                  <div className="text-sm text-muted-foreground">SELL Signals</div>
                </div>
                <div className="text-center p-4">
                  <div className="text-3xl font-bold text-yellow-600">
                    {resonancePoints.length}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Resonance</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
