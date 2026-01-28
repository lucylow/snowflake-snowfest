"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { QualityMetrics } from "@/lib/api-client"
import { TrendingUp, AlertCircle, CheckCircle2, Info } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface AlphaFoldQualityMetricsProps {
  qualityMetrics: QualityMetrics
  plddtScore?: number
}

export function AlphaFoldQualityMetrics({ qualityMetrics, plddtScore }: AlphaFoldQualityMetricsProps) {
  const metrics = qualityMetrics
  const score = plddtScore ?? metrics.plddt_score

  // Calculate percentages
  const total = metrics.confidence_regions.very_high + 
                metrics.confidence_regions.confident + 
                metrics.confidence_regions.low + 
                metrics.confidence_regions.very_low
  
  const veryHighPercent = total > 0 ? (metrics.confidence_regions.very_high / total) * 100 : 0
  const confidentPercent = total > 0 ? (metrics.confidence_regions.confident / total) * 100 : 0
  const lowPercent = total > 0 ? (metrics.confidence_regions.low / total) * 100 : 0
  const veryLowPercent = total > 0 ? (metrics.confidence_regions.very_low / total) * 100 : 0

  // Determine overall quality
  const getQualityBadge = () => {
    if (score >= 90) {
      return <Badge className="bg-green-500">Very High Confidence</Badge>
    } else if (score >= 70) {
      return <Badge className="bg-blue-500">High Confidence</Badge>
    } else if (score >= 50) {
      return <Badge className="bg-yellow-500">Medium Confidence</Badge>
    } else {
      return <Badge className="bg-red-500">Low Confidence</Badge>
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Structure Quality Metrics</CardTitle>
              <CardDescription>AlphaFold confidence scores and quality assessment</CardDescription>
            </div>
            {getQualityBadge()}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Overall pLDDT Score */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Overall pLDDT Score</span>
              <span className="text-lg font-bold">{score.toFixed(1)}</span>
            </div>
            <Progress value={score} className="h-3" />
            <p className="text-xs text-muted-foreground mt-2">
              pLDDT (predicted LDDT-Cα) measures confidence in the predicted structure. 
              Scores above 90 indicate very high confidence, 70-90 are confident, 
              50-70 are low confidence, and below 50 are very low confidence.
            </p>
          </div>

          {/* PAE Score if available */}
          {metrics.pae_score !== null && metrics.pae_score !== undefined && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Predicted Aligned Error (PAE)</span>
                <span className="text-lg font-bold">{metrics.pae_score.toFixed(2)} Å</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Lower PAE values indicate higher confidence in relative positions of residues.
              </p>
            </div>
          )}

          {/* Confidence Regions Breakdown */}
          <div>
            <h4 className="text-sm font-semibold mb-4">Confidence Distribution</h4>
            <div className="space-y-3">
              {/* Very High Confidence */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span className="text-sm">Very High (≥90)</span>
                  </div>
                  <span className="text-sm font-medium">
                    {metrics.confidence_regions.very_high} residues ({veryHighPercent.toFixed(1)}%)
                  </span>
                </div>
                <Progress value={veryHighPercent} className="h-2 bg-green-500/20" />
              </div>

              {/* Confident */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-blue-500" />
                    <span className="text-sm">Confident (70-89)</span>
                  </div>
                  <span className="text-sm font-medium">
                    {metrics.confidence_regions.confident} residues ({confidentPercent.toFixed(1)}%)
                  </span>
                </div>
                <Progress value={confidentPercent} className="h-2 bg-blue-500/20" />
              </div>

              {/* Low Confidence */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-yellow-500" />
                    <span className="text-sm">Low (50-69)</span>
                  </div>
                  <span className="text-sm font-medium">
                    {metrics.confidence_regions.low} residues ({lowPercent.toFixed(1)}%)
                  </span>
                </div>
                <Progress value={lowPercent} className="h-2 bg-yellow-500/20" />
              </div>

              {/* Very Low Confidence */}
              {metrics.confidence_regions.very_low > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-500" />
                      <span className="text-sm">Very Low (&lt;50)</span>
                    </div>
                    <span className="text-sm font-medium">
                      {metrics.confidence_regions.very_low} residues ({veryLowPercent.toFixed(1)}%)
                    </span>
                  </div>
                  <Progress value={veryLowPercent} className="h-2 bg-red-500/20" />
                </div>
              )}
            </div>
          </div>

          {/* Structure Info */}
          <div className="pt-4 border-t">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Structure Length</p>
                <p className="text-lg font-semibold">{metrics.structure_length} residues</p>
              </div>
              {metrics.per_residue_plddt.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground">Residues Analyzed</p>
                  <p className="text-lg font-semibold">{metrics.per_residue_plddt.length}</p>
                </div>
              )}
            </div>
          </div>

          {/* Quality Warnings */}
          {score < 70 && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>Quality Notice</AlertTitle>
              <AlertDescription>
                This structure has lower confidence scores. Regions with low pLDDT scores 
                (&lt;70) should be interpreted with caution and may require experimental 
                validation.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
