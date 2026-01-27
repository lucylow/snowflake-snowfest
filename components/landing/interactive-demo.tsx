"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Upload, Play, Download, CheckCircle } from "lucide-react"
import { useState } from "react"

export function InteractiveDemo() {
  const [step, setStep] = useState(1)
  const [isRunning, setIsRunning] = useState(false)

  const runDemo = () => {
    setIsRunning(true)
    setStep(2)

    setTimeout(() => setStep(3), 2000)
    setTimeout(() => setStep(4), 4000)
    setTimeout(() => {
      setStep(5)
      setIsRunning(false)
    }, 6000)
  }

  const resetDemo = () => {
    setStep(1)
    setIsRunning(false)
  }

  return (
    <Card className="border-border bg-card">
      <CardContent className="p-8">
        <div className="grid lg:grid-cols-2 gap-8">
          <div>
            <h3 className="text-2xl font-bold mb-4">Try Molecular Docking</h3>
            <p className="text-muted-foreground mb-6">
              Upload sample protein and ligand files to see the docking process in action
            </p>

            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  1
                </div>
                <div className="flex-1">
                  <div className="font-semibold">Upload Files</div>
                  <div className="text-sm text-muted-foreground">Protein (PDB) & Ligand (SDF)</div>
                </div>
                {step >= 2 && <CheckCircle className="w-5 h-5 text-green-500" />}
              </div>

              <div className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  2
                </div>
                <div className="flex-1">
                  <div className="font-semibold">Configure Parameters</div>
                  <div className="text-sm text-muted-foreground">Set docking options</div>
                </div>
                {step >= 3 && <CheckCircle className="w-5 h-5 text-green-500" />}
              </div>

              <div className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    step >= 3 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  3
                </div>
                <div className="flex-1">
                  <div className="font-semibold">Run Docking</div>
                  <div className="text-sm text-muted-foreground">GPU-accelerated computation</div>
                </div>
                {step >= 4 && <CheckCircle className="w-5 h-5 text-green-500" />}
              </div>

              <div className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    step >= 4 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  4
                </div>
                <div className="flex-1">
                  <div className="font-semibold">AI Analysis</div>
                  <div className="text-sm text-muted-foreground">Intelligent insights generation</div>
                </div>
                {step >= 5 && <CheckCircle className="w-5 h-5 text-green-500" />}
              </div>

              <div className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    step >= 5 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  5
                </div>
                <div className="flex-1">
                  <div className="font-semibold">Download Results</div>
                  <div className="text-sm text-muted-foreground">Reports & visualizations</div>
                </div>
                {step >= 5 && <CheckCircle className="w-5 h-5 text-green-500" />}
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <Button onClick={runDemo} disabled={isRunning} className="gap-2">
                <Play className="w-4 h-4" />
                {isRunning ? "Running..." : "Run Demo"}
              </Button>
              {step === 5 && (
                <Button variant="outline" onClick={resetDemo} className="gap-2 bg-transparent">
                  Reset
                </Button>
              )}
            </div>
          </div>

          <div className="bg-muted rounded-lg p-6 flex items-center justify-center min-h-[400px]">
            {step === 1 && (
              <div className="text-center">
                <Upload className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">Click "Run Demo" to start</p>
              </div>
            )}
            {step === 2 && (
              <div className="text-center">
                <Badge variant="outline" className="mb-4">
                  Validating Files...
                </Badge>
                <p className="text-sm text-muted-foreground">Checking file integrity</p>
              </div>
            )}
            {step === 3 && (
              <div className="text-center">
                <Badge variant="outline" className="mb-4">
                  Docking in Progress...
                </Badge>
                <div className="w-32 h-1 bg-primary/20 rounded-full overflow-hidden mx-auto">
                  <div className="h-full bg-primary animate-pulse" style={{ width: "60%" }}></div>
                </div>
              </div>
            )}
            {step === 4 && (
              <div className="text-center">
                <Badge variant="outline" className="mb-4">
                  AI Analysis Running...
                </Badge>
                <p className="text-sm text-muted-foreground">Analyzing binding interactions</p>
              </div>
            )}
            {step === 5 && (
              <div className="text-center">
                <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                <p className="font-semibold mb-2">Docking Complete!</p>
                <Button variant="outline" size="sm" className="gap-2 bg-transparent">
                  <Download className="w-4 h-4" />
                  Download Report
                </Button>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
