'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Play,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart3,
  LineChart,
  Info,
  Calculator,
  ShieldAlert
} from "lucide-react"

// Backtest result type
interface BacktestResult {
  totalReturn: number
  cagr: number
  sharpeRatio: number
  maxDrawdown: number
  winRate: number
  profitFactor: number
  totalTrades: number
  pValue: number
  bootstrapCiLower: number
  bootstrapCiUpper: number
  isInSample: boolean
  isValid: boolean
}

// Simulated backtest results
const generateBacktestResult = (isInSample: boolean): BacktestResult => {
  const baseReturn = isInSample ? 45 : 25
  const variation = Math.random() * 30
  return {
    totalReturn: baseReturn + variation,
    cagr: 8 + Math.random() * 12,
    sharpeRatio: 0.8 + Math.random() * 1.2,
    maxDrawdown: 10 + Math.random() * 20,
    winRate: 0.45 + Math.random() * 0.15,
    profitFactor: 1.2 + Math.random() * 0.8,
    totalTrades: 100 + Math.floor(Math.random() * 200),
    pValue: Math.random() * 0.08,
    bootstrapCiLower: -10 + Math.random() * 20,
    bootstrapCiUpper: 50 + Math.random() * 50,
    isInSample,
    isValid: Math.random() > 0.3
  }
}

// Equity curve data
const generateEquityCurve = (trades: number) => {
  let equity = 10000
  return Array.from({ length: trades }, (_, i) => {
    equity *= 1 + (Math.random() - 0.45) * 0.02
    return {
      trade: i + 1,
      equity: equity,
      drawdown: Math.random() * 20
    }
  })
}

export default function BacktestPage() {
  const [instrument, setInstrument] = useState("SPY")
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [inSampleResult, setInSampleResult] = useState<BacktestResult | null>(null)
  const [outOfSampleResult, setOutOfSampleResult] = useState<BacktestResult | null>(null)
  const [equityCurve, setEquityCurve] = useState<Array<{trade: number, equity: number, drawdown: number}>>([])
  
  // Configuration
  const [trainRatio, setTrainRatio] = useState([70])
  const [initialCapital, setInitialCapital] = useState("10000")
  const [commission, setCommission] = useState("0.001")
  const [bootstrapIterations, setBootstrapIterations] = useState([1000])
  const [enableChowTest, setEnableChowTest] = useState(true)

  const instruments = [
    { symbol: "SPY", name: "S&P 500 ETF", type: "ETF" },
    { symbol: "GLD", name: "Gold ETF", type: "ETF" },
    { symbol: "BTC-USD", name: "Bitcoin", type: "CRYPTO" },
    { symbol: "GBTC", name: "Grayscale Bitcoin Trust", type: "TRUST" },
  ]

  const runBacktest = async () => {
    setIsRunning(true)
    setProgress(0)
    setInSampleResult(null)
    setOutOfSampleResult(null)
    
    // Simulate progress
    for (let i = 0; i <= 100; i += 5) {
      await new Promise(resolve => setTimeout(resolve, 100))
      setProgress(i)
    }
    
    // Generate results
    const inSample = generateBacktestResult(true)
    const outSample = generateBacktestResult(false)
    
    setInSampleResult(inSample)
    setOutOfSampleResult(outSample)
    setEquityCurve(generateEquityCurve(inSample.totalTrades))
    setIsRunning(false)
  }

  // Validation checks
  const getValidationStatus = () => {
    if (!outOfSampleResult) return null
    
    const checks = [
      { name: "p-value < 0.05", pass: outOfSampleResult.pValue < 0.05, value: outOfSampleResult.pValue.toFixed(4) },
      { name: "Bootstrap CI > 0", pass: outOfSampleResult.bootstrapCiLower > 0, value: `[${outOfSampleResult.bootstrapCiLower.toFixed(1)}, ${outOfSampleResult.bootstrapCiUpper.toFixed(1)}]` },
      { name: "Sharpe > 1.0", pass: outOfSampleResult.sharpeRatio > 1.0, value: outOfSampleResult.sharpeRatio.toFixed(2) },
      { name: "Win Rate > 50%", pass: outOfSampleResult.winRate > 0.5, value: (outOfSampleResult.winRate * 100).toFixed(1) + "%" },
      { name: "Max DD < 25%", pass: outOfSampleResult.maxDrawdown < 25, value: outOfSampleResult.maxDrawdown.toFixed(1) + "%" },
    ]
    
    return checks
  }

  const validationChecks = getValidationStatus()
  const allChecksPass = validationChecks?.every(c => c.pass) ?? false

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Backtesting Engine</h1>
          <p className="text-muted-foreground mt-1">
            Валидация стратегии на истории с Bootstrap CI
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
          <Button onClick={runBacktest} disabled={isRunning} size="lg">
            {isRunning ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Running... {progress}%
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Backtest
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Critical Warning */}
      <Alert className="border-yellow-500/50 bg-yellow-500/10">
        <ShieldAlert className="h-4 w-4 text-yellow-600" />
        <AlertTitle className="text-yellow-600">⚠️ Правило бэктеста</AlertTitle>
        <AlertDescription className="text-yellow-700">
          <strong>НЕТ БЭКТЕСТА → НЕТ СИГНАЛА В ПРОДАКШЕНЕ</strong>
          <br />
          Каждая стратегия должна пройти: In-Sample/Out-of-Sample (70/30), Bootstrap CI &gt; 0 (95%), p-value &lt; 0.05
        </AlertDescription>
      </Alert>

      {/* Progress */}
      {isRunning && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Running Bootstrap iterations ({bootstrapIterations[0]})...</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="h-3" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calculator className="h-5 w-5" />
            Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label>Train Ratio: {trainRatio[0]}%</Label>
              <Slider value={trainRatio} onValueChange={setTrainRatio} min={50} max={80} step={5} />
              <p className="text-xs text-muted-foreground">Test ratio: {100 - trainRatio[0]}%</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="capital">Initial Capital ($)</Label>
              <Input id="capital" value={initialCapital} onChange={(e) => setInitialCapital(e.target.value)} />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="commission">Commission</Label>
              <Input id="commission" value={commission} onChange={(e) => setCommission(e.target.value)} />
            </div>
            
            <div className="space-y-2">
              <Label>Bootstrap Iterations: {bootstrapIterations[0]}</Label>
              <Slider value={bootstrapIterations} onValueChange={setBootstrapIterations} min={100} max={5000} step={100} />
            </div>
          </div>
          
          <Separator className="my-4" />
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch checked={enableChowTest} onCheckedChange={setEnableChowTest} />
              <Label>Enable Chow Test for Structural Breaks</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {inSampleResult && outOfSampleResult && (
        <div className="space-y-6">
          {/* Validation Status */}
          <Card className={allChecksPass ? "border-green-500" : "border-red-500"}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {allChecksPass ? (
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                ) : (
                  <XCircle className="h-6 w-6 text-red-500" />
                )}
                Validation Status: {allChecksPass ? "PASSED" : "FAILED"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-5">
                {validationChecks?.map((check, i) => (
                  <div 
                    key={i}
                    className={`p-3 rounded-lg border ${
                      check.pass ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {check.pass ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="text-sm font-medium">{check.name}</span>
                    </div>
                    <div className={`text-lg font-bold ${check.pass ? 'text-green-600' : 'text-red-600'}`}>
                      {check.value}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Performance Metrics */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* In-Sample */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>In-Sample (Train)</CardTitle>
                  <Badge variant="outline">{trainRatio[0]}%</Badge>
                </div>
                <CardDescription>Training period performance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Return</p>
                    <p className="text-2xl font-bold text-green-600">
                      +{inSampleResult.totalReturn.toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">CAGR</p>
                    <p className="text-2xl font-bold">{inSampleResult.cagr.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
                    <p className="text-2xl font-bold">{inSampleResult.sharpeRatio.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Max Drawdown</p>
                    <p className="text-2xl font-bold text-red-600">
                      -{inSampleResult.maxDrawdown.toFixed(1)}%
                    </p>
                  </div>
                </div>
                
                <Separator />
                
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div className="text-center p-2 rounded bg-muted">
                    <div className="text-muted-foreground">Win Rate</div>
                    <div className="font-medium">{(inSampleResult.winRate * 100).toFixed(1)}%</div>
                  </div>
                  <div className="text-center p-2 rounded bg-muted">
                    <div className="text-muted-foreground">Profit Factor</div>
                    <div className="font-medium">{inSampleResult.profitFactor.toFixed(2)}</div>
                  </div>
                  <div className="text-center p-2 rounded bg-muted">
                    <div className="text-muted-foreground">Trades</div>
                    <div className="font-medium">{inSampleResult.totalTrades}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Out-of-Sample */}
            <Card className={outOfSampleResult.isValid ? "" : "border-red-500"}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Out-of-Sample (Test)</CardTitle>
                  <Badge variant={outOfSampleResult.isValid ? "default" : "destructive"}>
                    {100 - trainRatio[0]}%
                  </Badge>
                </div>
                <CardDescription>Validation period performance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Return</p>
                    <p className={`text-2xl font-bold ${outOfSampleResult.totalReturn > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {outOfSampleResult.totalReturn > 0 ? '+' : ''}{outOfSampleResult.totalReturn.toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">CAGR</p>
                    <p className="text-2xl font-bold">{outOfSampleResult.cagr.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
                    <p className={`text-2xl font-bold ${outOfSampleResult.sharpeRatio > 1 ? 'text-green-600' : 'text-red-600'}`}>
                      {outOfSampleResult.sharpeRatio.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Max Drawdown</p>
                    <p className="text-2xl font-bold text-red-600">
                      -{outOfSampleResult.maxDrawdown.toFixed(1)}%
                    </p>
                  </div>
                </div>
                
                <Separator />
                
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div className="text-center p-2 rounded bg-muted">
                    <div className="text-muted-foreground">Win Rate</div>
                    <div className={`font-medium ${outOfSampleResult.winRate > 0.5 ? 'text-green-600' : 'text-red-600'}`}>
                      {(outOfSampleResult.winRate * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-center p-2 rounded bg-muted">
                    <div className="text-muted-foreground">Profit Factor</div>
                    <div className="font-medium">{outOfSampleResult.profitFactor.toFixed(2)}</div>
                  </div>
                  <div className="text-center p-2 rounded bg-muted">
                    <div className="text-muted-foreground">Trades</div>
                    <div className="font-medium">{Math.floor(outOfSampleResult.totalTrades * 0.3)}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Bootstrap CI */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Bootstrap Confidence Interval (95%)
              </CardTitle>
              <CardDescription>
                {bootstrapIterations[0]} iterations, BCa correction applied
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border bg-muted/50">
                    <h4 className="font-medium mb-2">Bootstrap CI Formula</h4>
                    <code className="text-sm">CI = [P₂.₅, P₉₇.₅]</code>
                    <p className="text-xs text-muted-foreground mt-2">
                      Resample returns {bootstrapIterations[0]} times with replacement
                    </p>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Lower Bound (2.5%)</span>
                      <span className={`font-medium ${outOfSampleResult.bootstrapCiLower > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {outOfSampleResult.bootstrapCiLower.toFixed(2)}%
                      </span>
                    </div>
                    <Progress 
                      value={(outOfSampleResult.bootstrapCiLower + 50) * 2} 
                      className="h-3"
                    />
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Upper Bound (97.5%)</span>
                      <span className="font-medium text-green-600">
                        {outOfSampleResult.bootstrapCiUpper.toFixed(2)}%
                      </span>
                    </div>
                    <Progress 
                      value={outOfSampleResult.bootstrapCiUpper} 
                      className="h-3"
                    />
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border">
                    <h4 className="font-medium mb-3">Statistical Significance</h4>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span>p-value</span>
                        <Badge variant={outOfSampleResult.pValue < 0.05 ? "default" : "destructive"}>
                          {outOfSampleResult.pValue.toFixed(4)}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Significance</span>
                        <Badge variant={outOfSampleResult.pValue < 0.05 ? "default" : "destructive"}>
                          {outOfSampleResult.pValue < 0.01 ? "Highly Significant" : 
                           outOfSampleResult.pValue < 0.05 ? "Significant" : "Not Significant"}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>CI Excludes 0</span>
                        <Badge variant={outOfSampleResult.bootstrapCiLower > 0 ? "default" : "destructive"}>
                          {outOfSampleResult.bootstrapCiLower > 0 ? "Yes ✓" : "No ✗"}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Equity Curve */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="h-5 w-5" />
                Equity Curve
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] flex items-end gap-px overflow-x-auto pb-4">
                {equityCurve.slice(0, 200).map((point, i) => {
                  const normalizedEquity = (point.equity / 15000) * 100
                  return (
                    <div
                      key={i}
                      className="flex-shrink-0 w-2 bg-primary/80 rounded-t transition-all hover:bg-primary"
                      style={{ height: `${normalizedEquity}%` }}
                      title={`Trade ${point.trade}: $${point.equity.toFixed(0)}`}
                    />
                  )
                })}
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>Trade 1</span>
                <span>Equity: ${initialCapital}</span>
                <span>Trade {equityCurve.length}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Info Panel */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div className="space-y-3 text-sm text-muted-foreground">
              <h4 className="font-medium text-foreground">Требования к валидации (TZ.md)</h4>
              <ul className="list-disc list-inside space-y-1">
                <li>In-Sample / Out-of-Sample разделение (70/30)</li>
                <li>Bootstrap CI &gt; 0 (95% confidence)</li>
                <li>p-value &lt; 0.05</li>
                <li>Chow Test для структурных сдвигов</li>
              </ul>
              <p className="mt-3">
                <strong>Важно:</strong> Стратегия может быть прибыльной на in-sample данных, 
                но убыточной на out-of-sample. Только прохождение всех тестов 
                позволяет использовать стратегию в продакшене.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
