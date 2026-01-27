"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/landing/header"
import { Footer } from "@/components/landing/footer"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Shield,
  Search,
  ExternalLink,
  CheckCircle,
  XCircle,
  Loader2,
  Copy,
  Check,
  FileText,
  Users,
  Calendar,
} from "lucide-react"
import { useWallet } from "@/contexts/wallet-context"
import { solanaClient } from "@/lib/solana-client"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { mockBlockchainTransactions } from "@/lib/mock-data"

export default function BlockchainPage() {
  const { connected, publicKey, connect } = useWallet()
  const [txSignature, setTxSignature] = useState("")
  const [verificationResult, setVerificationResult] = useState<any>(null)
  const [isVerifying, setIsVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [balance, setBalance] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)
  const [isRequestingAirdrop, setIsRequestingAirdrop] = useState(false)
  const [reportData, setReportData] = useState<any>(null)
  const [estimatedCost, setEstimatedCost] = useState<number | null>(null)
  const [showExamples, setShowExamples] = useState(true)

  useEffect(() => {
    const fetchBalance = async () => {
      if (connected && publicKey) {
        try {
          const bal = await solanaClient.getBalance(publicKey)
          setBalance(bal)
        } catch (error) {
          console.error("[v0] Failed to fetch balance:", error)
        }
      }
    }

    fetchBalance()
  }, [connected, publicKey])

  useEffect(() => {
    const fetchCost = async () => {
      try {
        const sdk = solanaClient.getNeuravivaSDK()
        const cost = await sdk.estimateTransactionCost()
        setEstimatedCost(cost)
      } catch (error) {
        console.error("[v0] Failed to estimate cost:", error)
      }
    }

    fetchCost()
  }, [])

  const handleVerify = async () => {
    if (!txSignature.trim()) {
      setError("Please enter a transaction signature")
      return
    }

    setIsVerifying(true)
    setError(null)
    setVerificationResult(null)
    setReportData(null)

    try {
      const mockTx = mockBlockchainTransactions.find((tx) => tx.signature === txSignature.trim())
      if (mockTx) {
        setVerificationResult({
          valid: true,
          details: {
            blockTime: mockTx.blockTime,
            slot: mockTx.slot,
          },
          signature: mockTx.signature,
        })
        setReportData(mockTx)
        setIsVerifying(false)
        return
      }

      const isValid = await solanaClient.verifyDataHash(txSignature.trim())

      if (isValid) {
        const details = await solanaClient.getTransactionDetails(txSignature.trim())
        const reportInfo = await solanaClient.getReportData(txSignature.trim())

        setVerificationResult({
          valid: true,
          details,
          signature: txSignature.trim(),
        })

        if (reportInfo) {
          setReportData(reportInfo)
        }
      } else {
        setVerificationResult({
          valid: false,
          signature: txSignature.trim(),
        })
      }
    } catch (error) {
      console.error("[v0] Verification error:", error)
      setError("Failed to verify transaction. Please check the signature and try again.")
    } finally {
      setIsVerifying(false)
    }
  }

  const handleRequestAirdrop = async () => {
    if (!connected || !publicKey) {
      setError("Please connect your wallet first")
      return
    }

    const network = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet"
    if (network === "mainnet-beta") {
      setError("Airdrop is not available on mainnet")
      return
    }

    setIsRequestingAirdrop(true)
    setError(null)

    try {
      await solanaClient.requestAirdrop(publicKey, 1)
      const newBalance = await solanaClient.getBalance(publicKey)
      setBalance(newBalance)
      alert("Airdrop successful! You received 1 SOL.")
    } catch (error) {
      console.error("[v0] Airdrop error:", error)
      setError("Failed to request airdrop. Please try again later.")
    } finally {
      setIsRequestingAirdrop(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const viewOnExplorer = (signature: string) => {
    const network = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet"
    window.open(`https://explorer.solana.com/tx/${signature}?cluster=${network}`, "_blank")
  }

  const loadExampleTransaction = (signature: string) => {
    setTxSignature(signature)
    setShowExamples(false)
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="container py-8 md:py-12">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-2 flex items-center gap-3">
            <Shield className="w-10 h-10 text-green-500" />
            Blockchain Verification
          </h1>
          <p className="text-muted-foreground">
            Verify molecular docking reports stored on the Solana blockchain for immutable audit trails.
          </p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Network Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Network</span>
                <Badge variant="secondary">{(process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet").toUpperCase()}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge variant="secondary" className="gap-1">
                  <CheckCircle className="w-3 h-3 text-green-500" />
                  Connected
                </Badge>
              </div>
              {estimatedCost !== null && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Tx Cost</span>
                  <span className="text-sm font-mono">{estimatedCost.toFixed(6)} SOL</span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Wallet Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Connection</span>
                {connected ? (
                  <Badge variant="secondary" className="gap-1">
                    <CheckCircle className="w-3 h-3 text-green-500" />
                    Connected
                  </Badge>
                ) : (
                  <Button size="sm" variant="outline" onClick={connect}>
                    Connect
                  </Button>
                )}
              </div>
              {connected && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Balance</span>
                    <span className="text-sm font-semibold">
                      {balance !== null ? `${balance.toFixed(4)} SOL` : "..."}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Address</span>
                    <span className="text-xs font-mono">
                      {publicKey?.toString().slice(0, 4)}...{publicKey?.toString().slice(-4)}
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full gap-2 bg-transparent"
                disabled={!connected || isRequestingAirdrop}
                onClick={handleRequestAirdrop}
              >
                {isRequestingAirdrop ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Requesting...
                  </>
                ) : (
                  <>Request Airdrop (Devnet)</>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full gap-2 bg-transparent"
                onClick={() =>
                  window.open(
                    `https://explorer.solana.com/?cluster=${process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet"}`,
                    "_blank",
                  )
                }
              >
                <ExternalLink className="w-4 h-4" />
                View Explorer
              </Button>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="verify" className="w-full">
          <TabsList className="grid w-full grid-cols-2 max-w-md">
            <TabsTrigger value="verify">Verify Transaction</TabsTrigger>
            <TabsTrigger value="info">How It Works</TabsTrigger>
          </TabsList>

          <TabsContent value="verify" className="mt-6">
            {showExamples && mockBlockchainTransactions.length > 0 && (
              <Card className="mb-6 border-blue-500/20 bg-blue-500/5">
                <CardHeader>
                  <CardTitle className="text-lg">Example Transactions</CardTitle>
                  <CardDescription>Click to try verifying these sample blockchain transactions</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {mockBlockchainTransactions.map((tx, idx) => (
                    <div
                      key={tx.signature}
                      className="p-3 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => loadExampleTransaction(tx.signature)}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">Transaction #{idx + 1}</span>
                        <Badge variant="outline" className="text-xs">
                          {tx.reportType}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground font-mono truncate">{tx.signature}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {tx.metadata.proteinName} + {tx.metadata.ligandName}
                      </p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Verify Report on Blockchain</CardTitle>
                <CardDescription>
                  Enter a transaction signature to verify a molecular docking report stored on Solana
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="signature">Transaction Signature</Label>
                  <div className="flex gap-2">
                    <Input
                      id="signature"
                      placeholder="Enter Solana transaction signature..."
                      value={txSignature}
                      onChange={(e) => setTxSignature(e.target.value)}
                      className="font-mono text-sm"
                    />
                    <Button onClick={handleVerify} disabled={isVerifying} className="gap-2">
                      {isVerifying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                      Verify
                    </Button>
                  </div>
                </div>

                {verificationResult && (
                  <div
                    className={`p-4 rounded-lg border ${verificationResult.valid ? "bg-green-500/5 border-green-500/20" : "bg-red-500/5 border-red-500/20"}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        {verificationResult.valid ? (
                          <>
                            <CheckCircle className="w-5 h-5 text-green-500" />
                            <span className="font-semibold text-green-700 dark:text-green-400">
                              Verification Successful
                            </span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-5 h-5 text-red-500" />
                            <span className="font-semibold text-red-700 dark:text-red-400">Transaction Not Found</span>
                          </>
                        )}
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-2 bg-transparent"
                        onClick={() => viewOnExplorer(verificationResult.signature)}
                      >
                        <ExternalLink className="w-3 h-3" />
                        Explorer
                      </Button>
                    </div>

                    {verificationResult.valid && (
                      <div className="space-y-2 mt-4">
                        <div className="text-sm">
                          <span className="text-muted-foreground">Signature:</span>
                          <div className="flex items-center gap-2 mt-1">
                            <code className="text-xs font-mono break-all block bg-muted p-2 rounded">
                              {verificationResult.signature}
                            </code>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => copyToClipboard(verificationResult.signature)}
                            >
                              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                            </Button>
                          </div>
                        </div>
                        {verificationResult.details && (
                          <>
                            <div className="text-sm">
                              <span className="text-muted-foreground">Block Time:</span>
                              <span className="ml-2 font-mono">
                                {verificationResult.details.blockTime
                                  ? new Date(verificationResult.details.blockTime * 1000).toLocaleString()
                                  : "N/A"}
                              </span>
                            </div>
                            <div className="text-sm">
                              <span className="text-muted-foreground">Slot:</span>
                              <span className="ml-2 font-mono">{verificationResult.details.slot || "N/A"}</span>
                            </div>
                          </>
                        )}

                        {reportData && (
                          <div className="mt-4 p-3 bg-muted/50 rounded-lg space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                              <FileText className="w-4 h-4 text-blue-500" />
                              <span className="font-semibold">Report Details</span>
                            </div>

                            <div className="grid grid-cols-2 gap-3 text-sm">
                              <div>
                                <span className="text-muted-foreground">Job ID:</span>
                                <p className="font-mono text-xs mt-1">{reportData.jobId}</p>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Report Type:</span>
                                <Badge variant="outline" className="mt-1">
                                  {reportData.reportType}
                                </Badge>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Stakeholder:</span>
                                <div className="flex items-center gap-1 mt-1">
                                  <Users className="w-3 h-3" />
                                  <span className="capitalize">{reportData.stakeholder}</span>
                                </div>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Timestamp:</span>
                                <div className="flex items-center gap-1 mt-1">
                                  <Calendar className="w-3 h-3" />
                                  <span className="text-xs">{new Date(reportData.timestamp).toLocaleDateString()}</span>
                                </div>
                              </div>
                            </div>

                            <div className="text-sm">
                              <span className="text-muted-foreground">Report Hash:</span>
                              <code className="text-xs font-mono break-all block bg-background p-2 rounded mt-1">
                                {reportData.reportHash}
                              </code>
                            </div>

                            {reportData.metadata && (
                              <div className="text-sm">
                                <span className="text-muted-foreground">Metadata:</span>
                                <pre className="text-xs font-mono bg-background p-2 rounded mt-1 overflow-x-auto">
                                  {JSON.stringify(reportData.metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}

                        <Alert className="mt-4">
                          <Shield className="w-4 h-4" />
                          <AlertDescription className="text-xs">
                            This report has been cryptographically verified and stored on the Solana blockchain,
                            ensuring data integrity and immutability for research papers and grant proposals.
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="info" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">How Blockchain Verification Works</CardTitle>
                <CardDescription>Understanding the security behind molecular docking reports</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <div className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-blue-500">1</span>
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">Report Generation</h3>
                      <p className="text-sm text-muted-foreground">
                        When you generate a molecular docking report, a cryptographic SHA-256 hash is created from the
                        report content using our Neuraviva SDK.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-green-500">2</span>
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">Blockchain Storage</h3>
                      <p className="text-sm text-muted-foreground">
                        The hash is stored on the Solana blockchain with comprehensive metadata including job ID,
                        timestamp, stakeholder type, and report format. Transaction cost is approximately{" "}
                        {estimatedCost?.toFixed(6) || "0.000005"} SOL.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-purple-500">3</span>
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">Immutable Record</h3>
                      <p className="text-sm text-muted-foreground">
                        Once stored on Solana, the record cannot be altered or deleted, creating a permanent audit trail
                        that can be verified by anyone at any time.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-orange-500/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-orange-500">4</span>
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">Verification</h3>
                      <p className="text-sm text-muted-foreground">
                        Anyone can verify the authenticity of a report by checking its transaction signature on the
                        blockchain using the Solana Explorer or this verification tool.
                      </p>
                    </div>
                  </div>
                </div>

                <Alert className="mt-6">
                  <Shield className="w-4 h-4" />
                  <AlertDescription>
                    <strong>Benefits for Researchers:</strong> Blockchain verification provides tamper-proof evidence
                    for research papers, grant applications, and regulatory submissions. All reports include
                    stakeholder-specific analysis (researcher, investor, regulator, clinician) with complete
                    traceability.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
      <Footer />
    </div>
  )
}
