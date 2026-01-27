"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { FileText, Loader2, Download, Shield, CheckCircle, ExternalLink, Users } from "lucide-react"
import { useWallet } from "@/contexts/wallet-context"
import { solanaClient } from "@/lib/solana-client"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface ReportGeneratorProps {
  jobId: string
}

export function ReportGenerator({ jobId }: ReportGeneratorProps) {
  const { wallet, connected, connect } = useWallet()
  const [reportType, setReportType] = useState<"pdf" | "html" | "json">("pdf")
  const [stakeholderType, setStakeholderType] = useState<"researcher" | "investor" | "regulator" | "clinician">(
    "researcher",
  )
  const [includeVisualizations, setIncludeVisualizations] = useState(true)
  const [storeOnBlockchain, setStoreOnBlockchain] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [reportUrl, setReportUrl] = useState<string | null>(null)
  const [blockchainTx, setBlockchainTx] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async () => {
    setIsGenerating(true)
    setError(null)

    try {
      if (storeOnBlockchain && !connected) {
        await connect()
        if (!connected) {
          throw new Error("Please connect your Phantom wallet to store on blockchain")
        }
      }

      await new Promise((resolve) => setTimeout(resolve, 3000))

      const mockReportUrl = `https://reports.snowflake.com/${jobId}/${stakeholderType}_report.${reportType}`
      setReportUrl(mockReportUrl)

      if (storeOnBlockchain && connected && wallet) {
        try {
          const result = await solanaClient.storeReportWithSDK(wallet, {
            jobId,
            reportContent: mockReportUrl,
            reportType,
            stakeholder: stakeholderType,
            metadata: {
              includeVisualizations,
              generatedBy: "SNOWFLAKE AI",
              version: "2.0",
            },
          })

          if (result.success && result.signature) {
            setBlockchainTx(result.signature)
            console.log("[v0] Report stored on blockchain:", result.signature)
            console.log("[v0] Explorer URL:", result.explorerUrl)
          } else {
            throw new Error(result.error || "Blockchain storage failed")
          }
        } catch (blockchainError) {
          console.error("[v0] Blockchain storage error:", blockchainError)
          setError("Report generated but blockchain storage failed. You can try again later.")
        }
      }
    } catch (error) {
      console.error("[v0] Report generation error:", error)
      setError(error instanceof Error ? error.message : "Failed to generate report. Please try again.")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = () => {
    if (reportUrl) {
      window.open(reportUrl, "_blank")
    }
  }

  const viewOnExplorer = () => {
    if (blockchainTx) {
      const network = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet"
      window.open(`https://explorer.solana.com/tx/${blockchainTx}?cluster=${network}`, "_blank")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-500" />
          Report Generation
        </CardTitle>
        <CardDescription>Generate stakeholder-specific reports with blockchain verification</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="stakeholder" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Target Audience
            </Label>
            <Select value={stakeholderType} onValueChange={(value: any) => setStakeholderType(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="researcher">
                  <div className="flex flex-col items-start">
                    <span className="font-medium">Researcher</span>
                    <span className="text-xs text-muted-foreground">Technical, method-focused</span>
                  </div>
                </SelectItem>
                <SelectItem value="investor">
                  <div className="flex flex-col items-start">
                    <span className="font-medium">Investor</span>
                    <span className="text-xs text-muted-foreground">Business, ROI-focused</span>
                  </div>
                </SelectItem>
                <SelectItem value="regulator">
                  <div className="flex flex-col items-start">
                    <span className="font-medium">Regulator</span>
                    <span className="text-xs text-muted-foreground">Compliance, safety-focused</span>
                  </div>
                </SelectItem>
                <SelectItem value="clinician">
                  <div className="flex flex-col items-start">
                    <span className="font-medium">Clinician</span>
                    <span className="text-xs text-muted-foreground">Patient, therapeutic-focused</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="report-format">Report Format</Label>
            <div className="flex gap-2">
              {(["pdf", "html", "json"] as const).map((type) => (
                <Button
                  key={type}
                  variant={reportType === type ? "default" : "outline"}
                  size="sm"
                  onClick={() => setReportType(type)}
                >
                  {type.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between py-2 border-b">
            <div className="space-y-0.5">
              <Label htmlFor="visualizations">Include Visualizations</Label>
              <p className="text-xs text-muted-foreground">Add 3D structures and analysis plots</p>
            </div>
            <Switch id="visualizations" checked={includeVisualizations} onCheckedChange={setIncludeVisualizations} />
          </div>

          <div className="flex items-center justify-between py-2 border-b">
            <div className="space-y-0.5">
              <Label htmlFor="blockchain" className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-green-500" />
                Store on Solana Blockchain
              </Label>
              <p className="text-xs text-muted-foreground">
                {connected ? "Create immutable audit trail" : "Connect wallet to enable"}
              </p>
            </div>
            <Switch
              id="blockchain"
              checked={storeOnBlockchain}
              onCheckedChange={setStoreOnBlockchain}
              disabled={!connected}
            />
          </div>

          {storeOnBlockchain && !connected && (
            <Alert>
              <Shield className="w-4 h-4" />
              <AlertDescription className="flex items-center justify-between">
                <span className="text-sm">Connect Phantom wallet to enable blockchain storage</span>
                <Button size="sm" variant="outline" onClick={connect}>
                  Connect
                </Button>
              </AlertDescription>
            </Alert>
          )}
        </div>

        <Button onClick={handleGenerate} disabled={isGenerating} className="w-full gap-2">
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating Report...
            </>
          ) : (
            <>
              <FileText className="w-4 h-4" />
              Generate {stakeholderType.charAt(0).toUpperCase() + stakeholderType.slice(1)} Report
            </>
          )}
        </Button>

        {reportUrl && (
          <div className="space-y-3 pt-4 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Report Ready</span>
              <Badge variant="secondary" className="gap-1">
                <CheckCircle className="w-3 h-3" />
                Success
              </Badge>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4" />
                <span className="text-sm font-medium">
                  {stakeholderType.charAt(0).toUpperCase() + stakeholderType.slice(1)} Report
                </span>
                <Badge variant="outline" className="text-xs">
                  {reportType.toUpperCase()}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {stakeholderType === "researcher" && "Includes detailed methodology and technical analysis"}
                {stakeholderType === "investor" && "Focuses on market opportunity and development timeline"}
                {stakeholderType === "regulator" && "Emphasizes safety, compliance, and documentation"}
                {stakeholderType === "clinician" && "Highlights therapeutic potential and clinical relevance"}
              </p>
            </div>
            <Button onClick={handleDownload} variant="outline" className="w-full gap-2 bg-transparent">
              <Download className="w-4 h-4" />
              Download Report
            </Button>
            {blockchainTx && (
              <div className="p-3 bg-muted rounded-lg space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-green-500" />
                    <span className="text-sm font-medium">Blockchain Verified</span>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    Solana
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground font-mono break-all">{blockchainTx}</p>
                <Button size="sm" variant="outline" className="w-full gap-2 bg-transparent" onClick={viewOnExplorer}>
                  <ExternalLink className="w-3 h-3" />
                  View on Solana Explorer
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
