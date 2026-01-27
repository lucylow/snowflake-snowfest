"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer } from "@/components/ui/chart"
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts"

export function DrugLikenessRadar() {
  const chartData = [
    { property: "Absorption", value: 85, fullMark: 100 },
    { property: "Distribution", value: 78, fullMark: 100 },
    { property: "Metabolism", value: 72, fullMark: 100 },
    { property: "Excretion", value: 80, fullMark: 100 },
    { property: "Toxicity", value: 88, fullMark: 100 },
    { property: "Solubility", value: 75, fullMark: 100 },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Drug-Likeness Profile (ADMET)</CardTitle>
        <CardDescription>Absorption, Distribution, Metabolism, Excretion, Toxicity analysis</CardDescription>
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
