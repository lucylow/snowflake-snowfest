"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { CheckCircle2, XCircle, AlertTriangle, Activity, Heart, Brain, FlaskConical, Droplets } from "lucide-react"

interface ADMETPropertiesPanelProps {
  admetData?: {
    absorption?: {
      gi_absorption?: { score?: number; prediction?: string }
      bioavailability?: { score?: number; prediction?: string; percentage?: number }
      solubility?: { log_s?: number; prediction?: string }
    }
    distribution?: {
      bbb_permeability?: { score?: number; prediction?: string; log_bb?: number }
      pgp_substrate?: { is_substrate?: boolean; probability?: number }
      vd_prediction?: { value?: number; interpretation?: string }
    }
    metabolism?: {
      cyp_inhibition?: Record<string, { probability?: number; likely?: boolean }>
      half_life?: { hours?: number; interpretation?: string }
      metabolic_stability?: { score?: number; prediction?: string }
    }
    excretion?: {
      clearance?: { value?: number; unit?: string; interpretation?: string }
      renal_clearance?: { value?: number; unit?: string; prediction?: string }
    }
  }
}

export function ADMETPropertiesPanel({ admetData }: ADMETPropertiesPanelProps) {
  if (!admetData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>ADMET Properties</CardTitle>
          <CardDescription>No ADMET data available</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const getScoreColor = (score: number) => {
    if (score > 0.7) return "text-green-600"
    if (score > 0.4) return "text-yellow-600"
    return "text-red-600"
  }

  const getBadgeVariant = (prediction?: string) => {
    if (!prediction) return "secondary"
    const lower = prediction.toLowerCase()
    if (lower.includes("high") || lower.includes("good") || lower.includes("permeant")) return "default"
    if (lower.includes("moderate") || lower.includes("medium")) return "secondary"
    return "destructive"
  }

  return (
    <div className="space-y-4">
      {/* Absorption */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            Absorption
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {admetData.absorption?.gi_absorption && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">GI Absorption</span>
                <Badge variant={getBadgeVariant(admetData.absorption.gi_absorption.prediction)}>
                  {admetData.absorption.gi_absorption.prediction || "N/A"}
                </Badge>
              </div>
              {admetData.absorption.gi_absorption.score !== undefined && (
                <Progress value={admetData.absorption.gi_absorption.score * 100} className="h-2" />
              )}
            </div>
          )}

          {admetData.absorption?.bioavailability && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Bioavailability</span>
                <div className="flex items-center gap-2">
                  <Badge variant={getBadgeVariant(admetData.absorption.bioavailability.prediction)}>
                    {admetData.absorption.bioavailability.prediction || "N/A"}
                  </Badge>
                  {admetData.absorption.bioavailability.percentage !== undefined && (
                    <span className="text-sm font-semibold">
                      {admetData.absorption.bioavailability.percentage.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
              {admetData.absorption.bioavailability.score !== undefined && (
                <Progress value={admetData.absorption.bioavailability.score * 100} className="h-2" />
              )}
            </div>
          )}

          {admetData.absorption?.solubility && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Solubility</span>
                <Badge variant={getBadgeVariant(admetData.absorption.solubility.prediction)}>
                  {admetData.absorption.solubility.prediction || "N/A"}
                </Badge>
              </div>
              {admetData.absorption.solubility.log_s !== undefined && (
                <p className="text-sm text-muted-foreground">
                  log S: {admetData.absorption.solubility.log_s.toFixed(2)}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-500" />
            Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {admetData.distribution?.bbb_permeability && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">BBB Permeability</span>
                <Badge variant={getBadgeVariant(admetData.distribution.bbb_permeability.prediction)}>
                  {admetData.distribution.bbb_permeability.prediction || "N/A"}
                </Badge>
              </div>
              {admetData.distribution.bbb_permeability.score !== undefined && (
                <Progress value={admetData.distribution.bbb_permeability.score * 100} className="h-2" />
              )}
              {admetData.distribution.bbb_permeability.log_bb !== undefined && (
                <p className="text-sm text-muted-foreground mt-1">
                  log BB: {admetData.distribution.bbb_permeability.log_bb.toFixed(3)}
                </p>
              )}
            </div>
          )}

          {admetData.distribution?.pgp_substrate && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">P-gp Substrate</span>
              {admetData.distribution.pgp_substrate.is_substrate ? (
                <Badge variant="destructive" className="gap-1">
                  <XCircle className="w-3 h-3" />
                  Yes
                </Badge>
              ) : (
                <Badge variant="default" className="gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  No
                </Badge>
              )}
            </div>
          )}

          {admetData.distribution?.vd_prediction && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Volume of Distribution</span>
                <Badge variant={getBadgeVariant(admetData.distribution.vd_prediction.interpretation)}>
                  {admetData.distribution.vd_prediction.interpretation || "N/A"}
                </Badge>
              </div>
              {admetData.distribution.vd_prediction.value !== undefined && (
                <p className="text-sm text-muted-foreground">
                  {admetData.distribution.vd_prediction.value.toFixed(2)} L/kg
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Metabolism */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-orange-500" />
            Metabolism
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {admetData.metabolism?.cyp_inhibition && (
            <div>
              <span className="text-sm font-medium mb-2 block">CYP450 Inhibition</span>
              <div className="space-y-2">
                {Object.entries(admetData.metabolism.cyp_inhibition).map(([cyp, data]) => (
                  <div key={cyp} className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{cyp.toUpperCase()}</span>
                    {data.likely ? (
                      <Badge variant="destructive" className="gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        High Risk
                      </Badge>
                    ) : (
                      <Badge variant="default" className="gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        Low Risk
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {admetData.metabolism?.half_life && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Half-Life</span>
                <Badge variant={getBadgeVariant(admetData.metabolism.half_life.interpretation)}>
                  {admetData.metabolism.half_life.interpretation || "N/A"}
                </Badge>
              </div>
              {admetData.metabolism.half_life.hours !== undefined && (
                <p className="text-sm text-muted-foreground">
                  {admetData.metabolism.half_life.hours.toFixed(1)} hours
                </p>
              )}
            </div>
          )}

          {admetData.metabolism?.metabolic_stability && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Metabolic Stability</span>
                <Badge variant={getBadgeVariant(admetData.metabolism.metabolic_stability.prediction)}>
                  {admetData.metabolism.metabolic_stability.prediction || "N/A"}
                </Badge>
              </div>
              {admetData.metabolism.metabolic_stability.score !== undefined && (
                <Progress value={admetData.metabolism.metabolic_stability.score * 100} className="h-2" />
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Excretion */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Droplets className="w-5 h-5 text-cyan-500" />
            Excretion
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {admetData.excretion?.clearance && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Clearance</span>
                <Badge variant={getBadgeVariant(admetData.excretion.clearance.interpretation)}>
                  {admetData.excretion.clearance.interpretation || "N/A"}
                </Badge>
              </div>
              {admetData.excretion.clearance.value !== undefined && (
                <p className="text-sm text-muted-foreground">
                  {admetData.excretion.clearance.value.toFixed(2)} {admetData.excretion.clearance.unit || "mL/min/kg"}
                </p>
              )}
            </div>
          )}

          {admetData.excretion?.renal_clearance && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Renal Clearance</span>
                <Badge variant={getBadgeVariant(admetData.excretion.renal_clearance.prediction)}>
                  {admetData.excretion.renal_clearance.prediction || "N/A"}
                </Badge>
              </div>
              {admetData.excretion.renal_clearance.value !== undefined && (
                <p className="text-sm text-muted-foreground">
                  {admetData.excretion.renal_clearance.value.toFixed(2)} {admetData.excretion.renal_clearance.unit || "mL/min/kg"}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
