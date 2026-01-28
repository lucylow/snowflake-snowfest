"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { AlertTriangle, CheckCircle2, XCircle, Activity, AlertCircle } from "lucide-react"

interface ToxicityPredictionsPanelProps {
  toxicityData?: {
    structural_alerts?: {
      count?: number
      alerts?: Array<{ name?: string; severity?: string }>
      risk_level?: string
    }
    ld50?: {
      value?: number
      unit?: string
      category?: string
      risk_level?: string
    }
    hepatotoxicity?: {
      probability?: number
      risk_level?: string
    }
    mutagenicity?: {
      ames_test?: { probability?: number }
      prediction?: string
    }
    carcinogenicity?: {
      probability?: number
      risk_level?: string
    }
    herg_inhibition?: {
      probability?: number
      risk_level?: string
    }
    skin_sensitization?: {
      probability?: number
      risk_level?: string
    }
    overall_toxicity_risk?: {
      score?: number
      level?: string
    }
  }
}

export function ToxicityPredictionsPanel({ toxicityData }: ToxicityPredictionsPanelProps) {
  if (!toxicityData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Toxicity Predictions</CardTitle>
          <CardDescription>No toxicity data available</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const getRiskColor = (level?: string) => {
    if (!level) return "text-gray-600"
    const lower = level.toLowerCase()
    if (lower === "low") return "text-green-600"
    if (lower === "moderate") return "text-yellow-600"
    return "text-red-600"
  }

  const getBadgeVariant = (level?: string) => {
    if (!level) return "secondary"
    const lower = level.toLowerCase()
    if (lower === "low") return "default"
    if (lower === "moderate") return "secondary"
    return "destructive"
  }

  const getRiskIcon = (level?: string) => {
    if (!level) return null
    const lower = level.toLowerCase()
    if (lower === "low") return <CheckCircle2 className="w-4 h-4 text-green-600" />
    if (lower === "moderate") return <AlertCircle className="w-4 h-4 text-yellow-600" />
    return <AlertTriangle className="w-4 h-4 text-red-600" />
  }

  return (
    <div className="space-y-4">
      {/* Overall Toxicity Risk */}
      {toxicityData.overall_toxicity_risk && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-red-500" />
              Overall Toxicity Risk
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Risk Score</span>
                <div className="flex items-center gap-2">
                  {getRiskIcon(toxicityData.overall_toxicity_risk.level)}
                  <Badge variant={getBadgeVariant(toxicityData.overall_toxicity_risk.level)}>
                    {toxicityData.overall_toxicity_risk.level?.toUpperCase() || "N/A"}
                  </Badge>
                </div>
              </div>
              {toxicityData.overall_toxicity_risk.score !== undefined && (
                <>
                  <Progress
                    value={(1 - toxicityData.overall_toxicity_risk.score) * 100}
                    className="h-3"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Score: {toxicityData.overall_toxicity_risk.score.toFixed(3)} (lower is better)
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Structural Alerts */}
      {toxicityData.structural_alerts && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              Structural Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-medium">Alerts Detected</span>
              <Badge variant={getBadgeVariant(toxicityData.structural_alerts.risk_level)}>
                {toxicityData.structural_alerts.count || 0}
              </Badge>
            </div>
            {toxicityData.structural_alerts.alerts && toxicityData.structural_alerts.alerts.length > 0 && (
              <div className="space-y-2">
                {toxicityData.structural_alerts.alerts.map((alert, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-muted rounded">
                    <span className="text-sm">{alert.name || `Alert ${idx + 1}`}</span>
                    <Badge variant={alert.severity === "high" ? "destructive" : "secondary"}>
                      {alert.severity || "moderate"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
            {(!toxicityData.structural_alerts.alerts || toxicityData.structural_alerts.alerts.length === 0) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                No structural alerts detected
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* LD50 */}
      {toxicityData.ld50 && (
        <Card>
          <CardHeader>
            <CardTitle>LD50 Prediction</CardTitle>
            <CardDescription>Predicted lethal dose (oral rat)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Value</span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold">
                  {toxicityData.ld50.value?.toFixed(1) || "N/A"}
                </span>
                <span className="text-sm text-muted-foreground">
                  {toxicityData.ld50.unit || "mg/kg"}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Category</span>
              <Badge variant={getBadgeVariant(toxicityData.ld50.risk_level)}>
                {toxicityData.ld50.category || "N/A"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Specific Toxicity Predictions */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Hepatotoxicity */}
        {toxicityData.hepatotoxicity && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Hepatotoxicity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Risk Level</span>
                <Badge variant={getBadgeVariant(toxicityData.hepatotoxicity.risk_level)}>
                  {toxicityData.hepatotoxicity.risk_level?.toUpperCase() || "N/A"}
                </Badge>
              </div>
              {toxicityData.hepatotoxicity.probability !== undefined && (
                <>
                  <Progress
                    value={toxicityData.hepatotoxicity.probability * 100}
                    className="h-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Probability: {(toxicityData.hepatotoxicity.probability * 100).toFixed(1)}%
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Mutagenicity */}
        {toxicityData.mutagenicity && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Mutagenicity (AMES)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Prediction</span>
                <Badge
                  variant={
                    toxicityData.mutagenicity.prediction?.toLowerCase() === "positive"
                      ? "destructive"
                      : "default"
                  }
                >
                  {toxicityData.mutagenicity.prediction?.toUpperCase() || "N/A"}
                </Badge>
              </div>
              {toxicityData.mutagenicity.ames_test?.probability !== undefined && (
                <>
                  <Progress
                    value={toxicityData.mutagenicity.ames_test.probability * 100}
                    className="h-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Probability: {(toxicityData.mutagenicity.ames_test.probability * 100).toFixed(1)}%
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Carcinogenicity */}
        {toxicityData.carcinogenicity && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Carcinogenicity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Risk Level</span>
                <Badge variant={getBadgeVariant(toxicityData.carcinogenicity.risk_level)}>
                  {toxicityData.carcinogenicity.risk_level?.toUpperCase() || "N/A"}
                </Badge>
              </div>
              {toxicityData.carcinogenicity.probability !== undefined && (
                <>
                  <Progress
                    value={toxicityData.carcinogenicity.probability * 100}
                    className="h-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Probability: {(toxicityData.carcinogenicity.probability * 100).toFixed(1)}%
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* hERG Inhibition */}
        {toxicityData.herg_inhibition && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">hERG Inhibition</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Risk Level</span>
                <Badge variant={getBadgeVariant(toxicityData.herg_inhibition.risk_level)}>
                  {toxicityData.herg_inhibition.risk_level?.toUpperCase() || "N/A"}
                </Badge>
              </div>
              {toxicityData.herg_inhibition.probability !== undefined && (
                <>
                  <Progress
                    value={toxicityData.herg_inhibition.probability * 100}
                    className="h-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Probability: {(toxicityData.herg_inhibition.probability * 100).toFixed(1)}%
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
