"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Brain, Sparkles, TrendingUp, Activity } from "lucide-react"

export function AIDemo() {
  return (
    <Card className="border-border bg-card">
      <CardContent className="p-8">
        <div className="grid lg:grid-cols-2 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-6 h-6 text-primary" />
              <h3 className="text-2xl font-bold">AI-Powered Drug Analysis</h3>
            </div>
            <p className="text-muted-foreground mb-6">
              Our AI analyzes binding affinity, ADMET properties, and therapeutic potential with stakeholder-specific
              insights for researchers, clinicians, investors, and regulators
            </p>

            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="outline">Researcher Perspective</Badge>
                  <Sparkles className="w-4 h-4 text-yellow-500" />
                </div>
                <p className="text-sm">
                  Strong hydrogen bonding with Met793 backbone and hydrophobic interactions in ATP pocket suggest
                  nanomolar IC50. Quinazoline scaffold favorable for kinase selectivity optimization.
                </p>
              </div>

              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="outline">Clinician Perspective</Badge>
                  <Activity className="w-4 h-4 text-blue-500" />
                </div>
                <p className="text-sm">
                  Favorable oral bioavailability (78%), low hepatotoxicity risk, and manageable side effect profile.
                  Suitable for first-line monotherapy in EGFR-mutant NSCLC patients.
                </p>
              </div>

              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="outline">Investor Perspective</Badge>
                  <TrendingUp className="w-4 h-4 text-green-500" />
                </div>
                <p className="text-sm">
                  Binding energy of -9.5 kcal/mol indicates strong commercial potential. Market size $8B+ for targeted
                  cancer therapies. Patent landscape favorable for next-generation derivatives.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <Card className="border-border">
              <CardContent className="p-4">
                <h4 className="font-semibold mb-2">Binding Affinity</h4>
                <div className="flex items-end gap-2">
                  <div className="text-3xl font-bold text-primary">-9.5</div>
                  <div className="text-muted-foreground mb-1">kcal/mol</div>
                </div>
                <div className="w-full h-2 bg-muted rounded-full mt-2">
                  <div className="h-full bg-primary rounded-full" style={{ width: "92%" }}></div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-4">
                <h4 className="font-semibold mb-2">Oral Bioavailability</h4>
                <div className="flex items-end gap-2">
                  <div className="text-3xl font-bold text-green-500">78%</div>
                </div>
                <div className="w-full h-2 bg-muted rounded-full mt-2">
                  <div className="h-full bg-green-500 rounded-full" style={{ width: "78%" }}></div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-4">
                <h4 className="font-semibold mb-2">ML Confidence Score</h4>
                <div className="flex items-end gap-2">
                  <div className="text-3xl font-bold text-blue-500">93%</div>
                </div>
                <div className="w-full h-2 bg-muted rounded-full mt-2">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: "93%" }}></div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
