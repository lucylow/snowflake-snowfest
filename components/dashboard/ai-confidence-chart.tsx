"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer } from "@/components/ui/chart"
import { RadialBar, RadialBarChart, PolarAngleAxis, ResponsiveContainer } from "recharts"

interface AIConfidenceChartProps {
  confidence: number
  analysisType: string
}

export function AIConfidenceChart({ confidence, analysisType }: AIConfidenceChartProps) {
  const chartData = [
    {
      name: "Confidence",
      value: confidence * 100,
      fill:
        confidence >= 0.8 ? "hsl(var(--chart-3))" : confidence >= 0.6 ? "hsl(var(--chart-4))" : "hsl(var(--chart-5))",
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Analysis Confidence</CardTitle>
        <CardDescription>{analysisType} prediction reliability</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            value: {
              label: "Confidence Score",
              color: "hsl(var(--chart-3))",
            },
          }}
          className="h-[250px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="90%"
              barSize={20}
              data={chartData}
              startAngle={90}
              endAngle={-270}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
              <RadialBar background dataKey="value" cornerRadius={10} />
              <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-foreground">
                <tspan x="50%" dy="-0.5em" fontSize="32" fontWeight="bold">
                  {Math.round(confidence * 100)}%
                </tspan>
                <tspan x="50%" dy="1.5em" fontSize="14" className="fill-muted-foreground">
                  Confidence
                </tspan>
              </text>
            </RadialBarChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
