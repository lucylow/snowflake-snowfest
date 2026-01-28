"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, FileText, FileJson, FileSpreadsheet } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface DockingMode {
  affinity?: number
  rmsd_lb?: number
  rmsd_ub?: number
}

interface DockingResult {
  ligand_name?: string
  modes?: DockingMode[]
  results?: Array<{
    ligand_name?: string
    modes?: DockingMode[]
  }>
}

interface DataExportProps {
  jobId: string
  dockingResults: DockingResult
  analysisResults?: Record<string, unknown>
}

export function DataExport({ jobId, dockingResults, analysisResults }: DataExportProps) {
  const [exportFormat, setExportFormat] = useState<"json" | "csv" | "tsv">("json")
  const [isExporting, setIsExporting] = useState(false)

  const exportData = async () => {
    setIsExporting(true)
    try {
      let content: string
      let filename: string
      let mimeType: string

      const data = {
        job_id: jobId,
        export_timestamp: new Date().toISOString(),
        docking_results: dockingResults,
        analysis_results: analysisResults,
      }

      if (exportFormat === "json") {
        content = JSON.stringify(data, null, 2)
        filename = `docking_analysis_${jobId}_${Date.now()}.json`
        mimeType = "application/json"
      } else {
        // Convert to CSV/TSV
        const delimiter = exportFormat === "csv" ? "," : "\t"
        const rows: string[] = []

        // Extract binding affinities
        const affinities: Array<{ ligand: string; pose: number; affinity: number; rmsd_lb?: number; rmsd_ub?: number }> = []

        dockingResults.results?.forEach((result: DockingResult) => {
          const modes = result.modes || []
          modes.forEach((mode: DockingMode, idx: number) => {
            if (mode.affinity !== undefined) {
              affinities.push({
                ligand: result.ligand_name || "unknown",
                pose: idx + 1,
                affinity: mode.affinity,
                rmsd_lb: mode.rmsd_lb,
                rmsd_ub: mode.rmsd_ub,
              })
            }
          })
        })

        // Header
        rows.push(["Ligand", "Pose", "Binding Affinity", "RMSD Lower", "RMSD Upper"].join(delimiter))

        // Data rows
        affinities.forEach((row) => {
          rows.push([row.ligand, row.pose.toString(), row.affinity.toString(), row.rmsd_lb?.toString() || "", row.rmsd_ub?.toString() || ""].join(delimiter))
        })

        // Add summary statistics
        if (affinities.length > 0) {
          const scores = affinities.map((a) => a.affinity)
          const mean = scores.reduce((a, b) => a + b, 0) / scores.length
          const min = Math.min(...scores)
          const max = Math.max(...scores)

          rows.push("")
          rows.push(["Statistic", "Value"].join(delimiter))
          rows.push(["Count", affinities.length.toString()].join(delimiter))
          rows.push(["Mean", mean.toFixed(4)].join(delimiter))
          rows.push(["Min", min.toFixed(4)].join(delimiter))
          rows.push(["Max", max.toFixed(4)].join(delimiter))
        }

        content = rows.join("\n")
        filename = `docking_analysis_${jobId}_${Date.now()}.${exportFormat}`
        mimeType = exportFormat === "csv" ? "text/csv" : "text/tab-separated-values"
      }

      // Create blob and download
      const blob = new Blob([content], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error("Export failed:", error)
      alert("Failed to export data. Please try again.")
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="w-5 h-5" />
          Data Export
        </CardTitle>
        <CardDescription>Export docking results and analysis data</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Export Format</label>
          <Select value={exportFormat} onValueChange={(value: "json" | "csv" | "tsv") => setExportFormat(value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="json">
                <div className="flex items-center gap-2">
                  <FileJson className="w-4 h-4" />
                  JSON (Complete Data)
                </div>
              </SelectItem>
              <SelectItem value="csv">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4" />
                  CSV (Spreadsheet)
                </div>
              </SelectItem>
              <SelectItem value="tsv">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  TSV (Tab-Separated)
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="p-4 bg-muted rounded-lg text-sm">
          <div className="font-medium mb-2">Export Includes:</div>
          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
            <li>All docking poses and binding affinities</li>
            <li>Ligand information</li>
            <li>Statistical summary</li>
            {analysisResults && <li>AI analysis results</li>}
          </ul>
        </div>

        <Button onClick={exportData} disabled={isExporting} className="w-full gap-2">
          {isExporting ? (
            <>
              <Download className="w-4 h-4 animate-pulse" />
              Exporting...
            </>
          ) : (
            <>
              <Download className="w-4 h-4" />
              Export Data
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
