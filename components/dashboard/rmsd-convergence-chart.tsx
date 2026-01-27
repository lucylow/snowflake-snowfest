"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Line, LineChart, CartesianGrid, XAxis, YAxis, ResponsiveContainer } from "recharts"

interface RMSDConvergenceChartProps {
  poses: Array<{ pose_id: number; score: number; rmsd: number }>
}

export function RMSDConvergenceChart({ poses }: RMSDConvergenceChartProps) {
  const chartData = poses.map((pose, idx) => ({
    name: `Pose ${idx + 1}`,
    rmsd: pose.rmsd,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>RMSD Convergence Analysis</CardTitle>
        <CardDescription>Root-mean-square deviation from best pose</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            rmsd: {
              label: "RMSD (Å)",
              color: "hsl(var(--chart-2))",
            },
          }}
          className="h-[300px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line type="monotone" dataKey="rmsd" stroke="var(--color-rmsd)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
