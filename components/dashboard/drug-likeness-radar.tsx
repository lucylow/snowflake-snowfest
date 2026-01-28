"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer } from "@/components/ui/chart"
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts"

interface DrugLikenessRadarProps {
  admetData?: {
    absorption?: {
      gi_absorption?: { score?: number }
      bioavailability?: { score?: number }
      solubility?: { score?: number }
    }
    distribution?: {
      bbb_permeability?: { score?: number }
      vd_prediction?: { value?: number }
    }
    metabolism?: {
      metabolic_stability?: { score?: number }
    }
    excretion?: {
      clearance?: { value?: number }
    }
  }
  toxicityData?: {
    overall_toxicity_risk?: {
      score?: number
    }
  }
}

export function DrugLikenessRadar({ admetData, toxicityData }: DrugLikenessRadarProps) {
  // Calculate scores from ADMET data or use defaults
  const absorptionScore = admetData?.absorption?.bioavailability?.score
    ? Math.round(admetData.absorption.bioavailability.score * 100)
    : admetData?.absorption?.gi_absorption?.score
    ? Math.round(admetData.absorption.gi_absorption.score * 100)
    : 75

  const distributionScore = admetData?.distribution?.bbb_permeability?.score
    ? Math.round(admetData.distribution.bbb_permeability.score * 100)
    : 70

  const metabolismScore = admetData?.metabolism?.metabolic_stability?.score
    ? Math.round(admetData.metabolism.metabolic_stability.score * 100)
    : 65

  const excretionScore = admetData?.excretion?.clearance?.value
    ? Math.max(0, Math.min(100, 100 - (admetData.excretion.clearance.value / 20) * 100))
    : 70

  const toxicityScore = toxicityData?.overall_toxicity_risk?.score
    ? Math.round((1 - toxicityData.overall_toxicity_risk.score) * 100)
    : 80

  const solubilityScore = admetData?.absorption?.solubility?.score
    ? Math.round(admetData.absorption.solubility.score * 100)
    : 70

  const chartData = [
    { property: "Absorption", value: absorptionScore, fullMark: 100 },
    { property: "Distribution", value: distributionScore, fullMark: 100 },
    { property: "Metabolism", value: metabolismScore, fullMark: 100 },
    { property: "Excretion", value: excretionScore, fullMark: 100 },
    { property: "Toxicity", value: toxicityScore, fullMark: 100 },
    { property: "Solubility", value: solubilityScore, fullMark: 100 },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Drug-Likeness Profile (ADMET)</CardTitle>
        <CardDescription>ML-powered analysis of Absorption, Distribution, Metabolism, Excretion, and Toxicity</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            value: {
              label: "Score",
              color: "hsl(var(--chart-1))",
            },
          }}
          className="h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={chartData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="property" />
              <PolarRadiusAxis angle={90} domain={[0, 100]} />
              <Radar
                name="Drug Properties"
                dataKey="value"
                stroke="hsl(var(--chart-1))"
                fill="hsl(var(--chart-1))"
                fillOpacity={0.6}
              />
            </RadarChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
