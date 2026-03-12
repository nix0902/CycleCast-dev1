'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  LineChart, 
  TrendingUp, 
  Activity, 
  BarChart3, 
  Zap,
  Target,
  CheckCircle2,
  Clock,
  Database,
  RefreshCw,
  Play,
  Settings,
  Calendar
} from "lucide-react"
import { useState } from "react"
import Link from "next/link"

export default function Home() {
  const [selectedInstrument, setSelectedInstrument] = useState("SPY")
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const phases = [
    { name: "Phase 0: Math Prototyping", progress: 100, status: "completed", tasks: 4 },
    { name: "Phase 1: Infrastructure", progress: 100, status: "completed", tasks: 1 },
    { name: "Phase 2: Seasonality Module", progress: 100, status: "completed", tasks: 5 },
    { name: "Phase 3: Integration", progress: 15, status: "in_progress", tasks: 7 },
  ]

  const instruments = [
    { symbol: "SPY", name: "S&P 500 ETF", type: "ETF" },
    { symbol: "GLD", name: "Gold ETF", type: "ETF" },
    { symbol: "BTC-USD", name: "Bitcoin", type: "CRYPTO" },
    { symbol: "GBTC", name: "Grayscale Bitcoin Trust", type: "TRUST" },
    { symbol: "GC=F", name: "Gold Futures", type: "FUTURES" },
  ]

  const features = [
    {
      icon: TrendingUp,
      title: "Annual Cycle / Seasonality",
      description: "Сезонный анализ с адаптивным FTE порогом",
      status: "ready"
    },
    {
      icon: LineChart,
      title: "QSpectrum",
      description: "Циклическая корреляция + МЭМ (Burg's method)",
      status: "ready"
    },
    {
      icon: BarChart3,
      title: "Composite Line",
      description: "Композитная линия прогноза (3 цикла, резонанс)",
      status: "ready"
    },
    {
      icon: Activity,
      title: "Phenomenological Model",
      description: "Исторические аналогии (DTW гибридный)",
      status: "ready"
    },
    {
      icon: Target,
      title: "COT/GBTC Analysis",
      description: "Анализ 'умных денег' (Percentile Rank)",
      status: "pending"
    },
    {
      icon: Zap,
      title: "Risk Management",
      description: "Position Sizing, Stop-Loss, Signal Decay",
      status: "pending"
    }
  ]

  const techStack = [
    { name: "Frontend", tech: "Next.js 16 + React 19 + TypeScript", status: "ready" },
    { name: "Database", tech: "SQLite + Prisma ORM", status: "ready" },
    { name: "Python Quant", tech: "NumPy, SciPy, Statsmodels", status: "ready" },
    { name: "UI Components", tech: "shadcn/ui + Tailwind CSS 4", status: "ready" },
    { name: "Charts", tech: "Recharts", status: "ready" },
    { name: "Backend (future)", tech: "Go 1.22+ (Clean Architecture)", status: "pending" },
  ]

  const cycles = [
    { period: 14, energy: 0.85, stability: 0.72, direction: "up" },
    { period: 42, energy: 0.72, stability: 0.65, direction: "up" },
    { period: 98, energy: 0.61, stability: 0.58, direction: "down" },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <LineChart className="h-8 w-8 text-primary" />
                <h1 className="text-2xl font-bold">CycleCast</h1>
                <Badge variant="secondary" className="ml-1">v3.2 Final</Badge>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Select value={selectedInstrument} onValueChange={setSelectedInstrument}>
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
              <Button 
                variant="default" 
                size="sm"
                onClick={() => setIsAnalyzing(true)}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Analysis
                  </>
                )}
              </Button>
              <Button variant="outline" size="icon">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Quick Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="bg-gradient-to-br from-green-500/10 to-green-500/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Фаз завершено</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">3 / 4</div>
              <Progress value={75} className="h-2 mt-2" />
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-blue-500/10 to-blue-500/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Python тесты</CardTitle>
              <Activity className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">~120 / 160</div>
              <p className="text-xs text-muted-foreground mt-1">75% pass rate</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-orange-500/10 to-orange-500/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Quant модули</CardTitle>
              <Database className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">4 / 4</div>
              <p className="text-xs text-muted-foreground mt-1">QSpectrum, Phenom, Bootstrap, Seasonality</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-purple-500/10 to-purple-500/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Статус</CardTitle>
              <Clock className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">Ready</div>
              <p className="text-xs text-muted-foreground mt-1">Phase 3 in progress</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="dashboard" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="cycles">Cycles</TabsTrigger>
            <TabsTrigger value="seasonality">Seasonality</TabsTrigger>
            <TabsTrigger value="progress">Progress</TabsTrigger>
            <TabsTrigger value="tech">Tech Stack</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            {/* Top Cycles */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Dominant Cycles</CardTitle>
                    <CardDescription>Top-3 cycles detected by QSpectrum</CardDescription>
                  </div>
                  <Badge variant="outline">{selectedInstrument}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  {cycles.map((cycle, index) => (
                    <div key={cycle.period} className="p-4 rounded-lg border bg-card">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant={index === 0 ? "default" : "secondary"}>
                          #{index + 1}
                        </Badge>
                        <Badge variant={cycle.direction === "up" ? "default" : "destructive"} className="text-xs">
                          {cycle.direction === "up" ? "↑ UP" : "↓ DOWN"}
                        </Badge>
                      </div>
                      <div className="text-3xl font-bold">{cycle.period}</div>
                      <p className="text-sm text-muted-foreground">days period</p>
                      <div className="mt-3 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Energy</span>
                          <span className="font-medium">{(cycle.energy * 100).toFixed(0)}%</span>
                        </div>
                        <Progress value={cycle.energy * 100} className="h-2" />
                        <div className="flex justify-between text-sm">
                          <span>Stability</span>
                          <span className="font-medium">{(cycle.stability * 100).toFixed(0)}%</span>
                        </div>
                        <Progress value={cycle.stability * 100} className="h-2" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Quick Links to Analysis Pages */}
            <div className="grid gap-4 md:grid-cols-4">
              <Link href="/analysis/seasonality">
                <Card className="cursor-pointer hover:border-primary transition-colors">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-6 w-6 text-primary" />
                      <CardTitle>Seasonality Analysis</CardTitle>
                    </div>
                    <CardDescription>
                      Annual Cycle с адаптивным FTE порогом
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      FTE валидация, Regime detection
                    </p>
                  </CardContent>
                </Card>
              </Link>
              <Link href="/analysis/decennial">
                <Card className="cursor-pointer hover:border-primary transition-colors">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-6 w-6 text-primary" />
                      <CardTitle>Decennial Pattern</CardTitle>
                    </div>
                    <CardDescription>
                      Larry Williams 10-year cycle patterns
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      Year digit analysis (0-9)
                    </p>
                  </CardContent>
                </Card>
              </Link>
              <Link href="/analysis/qspectrum">
                <Card className="cursor-pointer hover:border-primary transition-colors">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <LineChart className="h-6 w-6 text-primary" />
                      <CardTitle>QSpectrum Analysis</CardTitle>
                    </div>
                    <CardDescription>
                      Циклическая корреляция + Burg&apos;s MEM
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      Composite Line, резонанс
                    </p>
                  </CardContent>
                </Card>
              </Link>
              <Link href="/analysis/backtest">
                <Card className="cursor-pointer hover:border-primary transition-colors">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Activity className="h-6 w-6 text-primary" />
                      <CardTitle>Backtesting Engine</CardTitle>
                    </div>
                    <CardDescription>
                      Валидация стратегии с Bootstrap CI
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      In/Out-of-Sample, p-value
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </div>

            {/* Features Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {features.map((feature, index) => (
                <Card key={index} className={feature.status === "pending" ? "opacity-60" : ""}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <feature.icon className="h-8 w-8 text-primary" />
                      <Badge variant={feature.status === "ready" ? "default" : "secondary"}>
                        {feature.status}
                      </Badge>
                    </div>
                    <CardTitle className="text-lg mt-2">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="cycles" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>QSpectrum Analysis</CardTitle>
                <CardDescription>Cycle detection using Burg&apos;s Maximum Entropy Method</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border bg-muted/50">
                    <h3 className="font-semibold mb-2">Algorithm</h3>
                    <code className="text-sm text-muted-foreground">
                      C(period) = Σ P(t) × P(t-period) / (N - period)
                    </code>
                    <p className="text-sm text-muted-foreground mt-2">
                      E(period) = |C(period)| × √(N/period) × WFA_Stability
                    </p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="p-4 rounded-lg border">
                      <h4 className="font-medium mb-2">Dominant Period</h4>
                      <p className="text-3xl font-bold text-primary">14 days</p>
                      <p className="text-sm text-muted-foreground">Based on energy ranking</p>
                    </div>
                    <div className="p-4 rounded-lg border">
                      <h4 className="font-medium mb-2">Spectral Entropy</h4>
                      <p className="text-3xl font-bold text-primary">0.42</p>
                      <p className="text-sm text-muted-foreground">Lower = more cyclical</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="seasonality" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>FTE Validation</CardTitle>
                <CardDescription>Forecast Theoretical Efficiency with adaptive threshold</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="p-4 rounded-lg border bg-green-500/10">
                      <h4 className="font-medium mb-1">FTE Correlation</h4>
                      <p className="text-2xl font-bold text-green-500">0.72</p>
                      <p className="text-sm text-muted-foreground">Valid (&gt; 0.05)</p>
                    </div>
                    <div className="p-4 rounded-lg border bg-blue-500/10">
                      <h4 className="font-medium mb-1">Regime</h4>
                      <p className="text-2xl font-bold text-blue-500">NORMAL_VOL</p>
                      <p className="text-sm text-muted-foreground">Adaptive threshold: 0.058</p>
                    </div>
                    <div className="p-4 rounded-lg border bg-purple-500/10">
                      <h4 className="font-medium mb-1">p-value</h4>
                      <p className="text-2xl font-bold text-purple-500">0.023</p>
                      <p className="text-sm text-muted-foreground">Significant (&lt; 0.05)</p>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border bg-muted/50">
                    <h3 className="font-semibold mb-2">Adaptive Threshold Formula</h3>
                    <code className="text-sm text-muted-foreground">
                      threshold = base × (1 + λ × (current_vol / long_term_vol - 1))
                    </code>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="progress" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Project Progress</CardTitle>
                <CardDescription>44 weeks, 11 phases development roadmap</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {phases.map((phase, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{phase.name}</span>
                        <Badge variant={phase.status === "completed" ? "default" : phase.status === "in_progress" ? "secondary" : "outline"}>
                          {phase.status === "completed" ? "Завершено" : phase.status === "in_progress" ? "В работе" : "Ожидание"}
                        </Badge>
                      </div>
                      <Progress value={phase.progress} className="h-2" />
                      <p className="text-sm text-muted-foreground">
                        Задач: {phase.status === "completed" ? phase.tasks : phase.status === "in_progress" ? "1/" + phase.tasks : "0/" + phase.tasks}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tech" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Technology Stack</CardTitle>
                <CardDescription>Production-ready architecture</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {techStack.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-3">
                        <Database className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="font-medium">{item.name}</p>
                          <p className="text-sm text-muted-foreground">{item.tech}</p>
                        </div>
                      </div>
                      <Badge variant={item.status === "ready" ? "default" : "secondary"}>
                        {item.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t bg-card mt-auto">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              CycleCast v3.2 Final — Циклический анализ по методологии Ларри Вильямса
            </p>
            <div className="flex items-center gap-2">
              <Badge variant="outline">Next.js 16</Badge>
              <Badge variant="outline">TypeScript</Badge>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
