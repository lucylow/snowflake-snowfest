"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Shield, Lock, CheckCircle, ExternalLink } from "lucide-react"

export function BlockchainDemo() {
  return (
    <Card className="border-border bg-card">
      <CardContent className="p-8">
        <div className="grid lg:grid-cols-2 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-6 h-6 text-primary" />
              <h3 className="text-2xl font-bold">Blockchain Verification</h3>
            </div>
            <p className="text-muted-foreground mb-6">
              All docking results are stored on the Solana blockchain for immutable verification and audit trails
            </p>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-500 mt-1" />
                <div>
                  <div className="font-semibold">Immutable Storage</div>
                  <p className="text-sm text-muted-foreground">Results cannot be altered once stored</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-500 mt-1" />
                <div>
                  <div className="font-semibold">Cryptographic Verification</div>
                  <p className="text-sm text-muted-foreground">SHA-256 hashing ensures data integrity</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-500 mt-1" />
                <div>
                  <div className="font-semibold">Public Audit Trail</div>
                  <p className="text-sm text-muted-foreground">Anyone can verify results on-chain</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-500 mt-1" />
                <div>
                  <div className="font-semibold">Low Cost</div>
                  <p className="text-sm text-muted-foreground">Minimal transaction fees on Solana</p>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <Card className="border-border bg-muted/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold text-sm">Sample Transaction</h4>
                  <Badge variant="outline" className="gap-1">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    Verified
                  </Badge>
                </div>

                <div className="space-y-2 text-sm">
                  <div>
                    <div className="text-muted-foreground">Transaction ID</div>
                    <div className="font-mono text-xs break-all">5k2F...mN9x</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Block Height</div>
                    <div className="font-mono">245,789,123</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Report Hash</div>
                    <div className="font-mono text-xs break-all">a3b2...7f4e</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Timestamp</div>
                    <div>2024-12-31 14:23:45 UTC</div>
                  </div>
                </div>

                <Button variant="outline" size="sm" className="w-full mt-4 gap-2 bg-transparent">
                  <ExternalLink className="w-4 h-4" />
                  View on Solana Explorer
                </Button>
              </CardContent>
            </Card>

            <Card className="border-border bg-primary/5">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Lock className="w-4 h-4 text-primary" />
                  <h4 className="font-semibold text-sm">Security Features</h4>
                </div>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                    End-to-end encryption
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                    Multi-signature support
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                    Decentralized storage
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
