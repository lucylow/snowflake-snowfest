"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Sparkles, Loader2, Copy, Check, AlertCircle, TrendingUp, Activity, Zap } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { aiAgent, type AIAnalysisRequest } from "@/lib/ai-agent"
import { mockAIAnalyses } from "@/lib/mock-data"
import { AIConfidenceChart } from "./ai-confidence-chart"
import { DrugLikenessRadar } from "./drug-likeness-radar"
import { InteractionHeatmap } from "./interaction-heatmap"

interface AIAnalysisPanelProps {
  jobId: string
}

export function AIAnalysisPanel({ jobId }: AIAnalysisPanelProps) {
  const [analysisType, setAnalysisType] = useState<AIAnalysisRequest["analysisType"]>("comprehensive")
  const [stakeholderType, setStakeholderType] = useState<AIAnalysisRequest["stakeholderType"]>("researcher")
  const [customPrompt, setCustomPrompt] = useState("")
  const [result, setResult] = useState<any>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAnalyze = async () => {
    setIsAnalyzing(true)
    setError(null)

    try {
      const mockData = mockAIAnalyses[jobId as keyof typeof mockAIAnalyses]
      if (mockData) {
        await new Promise((resolve) => setTimeout(resolve, 1500))

        const stakeholderData = mockData[stakeholderType]
        setResult({
          analysis: {
            summary: stakeholderData.summary,
            detailed_analysis:
              stakeholderData.bindingAnalysis ||
              stakeholderData.marketOpportunity ||
              stakeholderData.safetyProfile ||
              stakeholderData.clinicalApplication ||
              {},
            limitations: [
              "Analysis based on computational predictions only",
              "Experimental validation required",
              "In vivo efficacy not confirmed",
            ],
          },
          recommendations: stakeholderData.recommendations || [],
          confidence: stakeholderData.confidence,
          metadata: {
            model: "gpt-4-turbo",
            costEstimate: 0.0234,
            processingTime: 1.5,
          },
        })
        setIsAnalyzing(false)
        return
      }

      const response = await aiAgent.analyzeDockingResults({
        jobId,
        analysisType,
        customPrompt: customPrompt || undefined,
        stakeholderType,
        includeVisualizations: true,
      })
      setResult(response)
    } catch (error) {
      console.error("[v0] AI analysis error:", error)
      setError(error instanceof Error ? error.message : "AI analysis failed. Please try again.")
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleCopy = async () => {
    if (result?.analysis) {
      try {
        await navigator.clipboard.writeText(JSON.stringify(result.analysis, null, 2))
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (error) {
        console.error("[v0] Copy failed:", error)
        setError("Failed to copy to clipboard")
      }
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-500" />
                AI-Powered Analysis
              </CardTitle>
              <CardDescription>Generate intelligent insights with stakeholder-specific recommendations</CardDescription>
            </div>
            {result && (
              <Badge variant="secondary" className="gap-1">
                <Check className="w-3 h-3" />
                Analysis Complete
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Analysis Type</label>
              <Select value={analysisType} onValueChange={(value: any) => setAnalysisType(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="binding_affinity">Binding Affinity</SelectItem>
                  <SelectItem value="drug_likeness">Drug Likeness</SelectItem>
                  <SelectItem value="toxicity">Toxicity Prediction</SelectItem>
                  <SelectItem value="comprehensive">Comprehensive Analysis</SelectItem>
                  <SelectItem value="custom">Custom Analysis</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Stakeholder Perspective</label>
              <Select value={stakeholderType} onValueChange={(value: any) => setStakeholderType(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="researcher">Researcher</SelectItem>
                  <SelectItem value="investor">Investor</SelectItem>
                  <SelectItem value="regulator">Regulator</SelectItem>
                  <SelectItem value="clinician">Clinician</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Custom Prompt (Optional)</label>
            <Textarea
              placeholder="Ask specific questions about the docking results..."
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              rows={3}
            />
          </div>

          <Button onClick={handleAnalyze} disabled={isAnalyzing} className="w-full gap-2">
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate Analysis
              </>
            )}
          </Button>

          {result && (
            <div className="space-y-6 pt-4 border-t">
              <div className="grid grid-cols-3 gap-3">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <TrendingUp className="w-4 h-4 text-green-500" />
                      <span className="text-xs text-muted-foreground">Confidence</span>
                    </div>
                    <p className="text-xl font-bold">{Math.round(result.confidence * 100)}%</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Activity className="w-4 h-4 text-blue-500" />
                      <span className="text-xs text-muted-foreground">Model</span>
                    </div>
                    <p className="text-sm font-semibold">{result.metadata.model}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Zap className="w-4 h-4 text-purple-500" />
                      <span className="text-xs text-muted-foreground">Cost</span>
                    </div>
                    <p className="text-xl font-bold">${result.metadata.costEstimate.toFixed(4)}</p>
                  </CardContent>
                </Card>
              </div>

              <div className="flex items-center justify-between">
                <h4 className="font-medium">Analysis Results</h4>
                <Button variant="ghost" size="sm" onClick={handleCopy} className="gap-2">
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? "Copied!" : "Copy"}
                </Button>
              </div>

              <div className="space-y-4">
                <div>
                  <h5 className="font-semibold mb-2">Summary</h5>
                  <div className="p-4 bg-muted rounded-lg text-sm leading-relaxed">{result.analysis.summary}</div>
                </div>

                {result.analysis.detailed_analysis && typeof result.analysis.detailed_analysis === "object" && (
                  <div>
                    <h5 className="font-semibold mb-2">Detailed Analysis</h5>
                    <div className="space-y-3">
                      {Object.entries(result.analysis.detailed_analysis).map(([key, value]) => (
                        <div key={key} className="p-3 bg-muted/50 rounded-lg">
                          <h6 className="text-sm font-medium capitalize mb-1">{key.replace(/_/g, " ")}</h6>
                          {typeof value === "object" ? (
                            <div className="space-y-1">
                              {Object.entries(value as Record<string, any>).map(([subKey, subValue]) => (
                                <div key={subKey} className="text-sm text-muted-foreground">
                                  <span className="font-medium capitalize">{subKey.replace(/_/g, " ")}:</span>{" "}
                                  {Array.isArray(subValue) ? (
                                    <ul className="ml-4 mt-1 space-y-1">
                                      {subValue.map((item, idx) => (
                                        <li key={idx}>• {item}</li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <span>{String(subValue)}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">{String(value)}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.recommendations && result.recommendations.length > 0 && (
                  <div>
                    <h5 className="font-semibold mb-2">Recommendations ({stakeholderType})</h5>
                    <ul className="space-y-2">
                      {result.recommendations.map((rec: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="text-primary mt-0.5">•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <h5 className="font-semibold mb-2">Limitations</h5>
                  <ul className="space-y-1">
                    {result.analysis.limitations.map((limitation: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-muted-foreground">
                        <span className="mt-0.5">⚠</span>
                        <span>{limitation}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <div className="grid lg:grid-cols-2 gap-6">
          <AIConfidenceChart confidence={result.confidence} analysisType={analysisType} />
          <DrugLikenessRadar />
          <InteractionHeatmap />
        </div>
      )}
    </div>
  )
}
