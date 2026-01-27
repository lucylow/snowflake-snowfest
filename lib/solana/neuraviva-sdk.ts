import { type Connection, PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js"
import { sha256 } from "js-sha256"

export interface ReportData {
  jobId: string
  reportHash: string
  reportType: string
  stakeholder: string
  metadata: any
  timestamp: number
  verified: boolean
  verifiedAt?: number
  validator?: string
  authority: string
  transactionHash: string
}

export interface StorageStats {
  totalReports: number
  authority: string
  createdAt: number
  updatedAt: number
}

export interface TransactionResult {
  success: boolean
  transactionHash: string
  signature?: string
  error?: string
  explorerUrl?: string
}

export class NeuravivaSDK {
  private connection: Connection
  private programId: PublicKey
  private network: string

  constructor(connection: Connection, network = "devnet") {
    this.connection = connection
    this.network = network
    this.programId = this.getProgramId(network)
  }

  private getProgramId(network: string): PublicKey {
    const programIds = {
      devnet: new PublicKey("NEURV111111111111111111111111111111111111111"),
      testnet: new PublicKey("NEURV222222222222222222222222222222222222222"),
      mainnet: new PublicKey("NEURV333333333333333333333333333333333333333"),
      localnet: new PublicKey("NEURV444444444444444444444444444444444444444"),
    }
    return programIds[network as keyof typeof programIds] || programIds.devnet
  }

  // Get PDA for report storage account
  async getReportStoragePDA(authority: PublicKey): Promise<[PublicKey, number]> {
    return PublicKey.findProgramAddress([Buffer.from("report-storage"), authority.toBuffer()], this.programId)
  }

  // Get PDA for specific report
  async getReportPDA(jobId: string, authority: PublicKey): Promise<[PublicKey, number]> {
    return PublicKey.findProgramAddress(
      [Buffer.from("report"), Buffer.from(jobId), authority.toBuffer()],
      this.programId,
    )
  }

  // Generate SHA-256 hash for report content
  generateReportHash(content: string | Buffer): string {
    const data = typeof content === "string" ? content : Buffer.from(content).toString()
    return sha256(data)
  }

  // Initialize report storage (first time setup)
  async initializeStorage(wallet: {
    publicKey: PublicKey
    signTransaction: (transaction: Transaction) => Promise<Transaction>
  }): Promise<TransactionResult> {
    try {
      const [reportStoragePDA] = await this.getReportStoragePDA(wallet.publicKey)

      // Check if already initialized
      const accountInfo = await this.connection.getAccountInfo(reportStoragePDA)
      if (accountInfo) {
        return {
          success: true,
          transactionHash: "",
          error: "Storage already initialized",
        }
      }

      // Create memo instruction for initialization
      const memoProgram = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
      const initData = JSON.stringify({
        type: "initialize_storage",
        authority: wallet.publicKey.toString(),
        timestamp: Date.now(),
      })

      const transaction = new Transaction().add({
        keys: [],
        programId: memoProgram,
        data: Buffer.from(initData),
      })

      const { blockhash, lastValidBlockHeight } = await this.connection.getLatestBlockhash()
      transaction.recentBlockhash = blockhash
      transaction.feePayer = wallet.publicKey

      const signedTx = await wallet.signTransaction(transaction)
      const signature = await this.connection.sendRawTransaction(signedTx.serialize())

      await this.connection.confirmTransaction({
        signature,
        blockhash,
        lastValidBlockHeight,
      })

      return {
        success: true,
        transactionHash: signature,
        signature,
        explorerUrl: `https://explorer.solana.com/tx/${signature}?cluster=${this.network}`,
      }
    } catch (error: any) {
      console.error("[v0] Failed to initialize storage:", error)
      return {
        success: false,
        transactionHash: "",
        error: error.message || "Failed to initialize storage",
      }
    }
  }

  // Store report hash with advanced metadata
  async storeReportHash(
    wallet: {
      publicKey: PublicKey
      signTransaction: (transaction: Transaction) => Promise<Transaction>
    },
    params: {
      jobId: string
      reportContent: string | Buffer
      reportType: string
      stakeholder: string
      metadata?: any
    },
  ): Promise<TransactionResult> {
    try {
      const { jobId, reportContent, reportType, stakeholder, metadata = {} } = params

      // Validate inputs
      if (jobId.length > 64) {
        throw new Error("Job ID too long (max 64 characters)")
      }
      if (reportType.length > 32) {
        throw new Error("Report type too long (max 32 characters)")
      }
      if (stakeholder.length > 32) {
        throw new Error("Stakeholder too long (max 32 characters)")
      }

      // Generate report hash
      const reportHash = this.generateReportHash(reportContent)

      // Prepare enhanced metadata
      const enhancedMetadata = {
        ...metadata,
        jobId,
        reportType,
        stakeholder,
        reportHash,
        contentLength: typeof reportContent === "string" ? reportContent.length : reportContent.byteLength,
        generatedAt: new Date().toISOString(),
        version: "1.0",
        sdk: "neuraviva-sdk",
      }

      const metadataString = JSON.stringify(enhancedMetadata)
      if (metadataString.length > 512) {
        throw new Error("Metadata too long (max 512 characters)")
      }

      // Get report PDA
      const [reportPDA] = await this.getReportPDA(jobId, wallet.publicKey)

      // Check if report already exists
      const existingReport = await this.connection.getAccountInfo(reportPDA)
      if (existingReport) {
        throw new Error("Report already stored for this job")
      }

      // Create transaction with memo program
      const memoProgram = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
      const reportData = JSON.stringify({
        type: "store_report",
        jobId,
        reportHash,
        reportType,
        stakeholder,
        metadata: enhancedMetadata,
        authority: wallet.publicKey.toString(),
        timestamp: Date.now(),
      })

      const transaction = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: wallet.publicKey,
          toPubkey: wallet.publicKey,
          lamports: 1,
        }),
        {
          keys: [],
          programId: memoProgram,
          data: Buffer.from(reportData),
        },
      )

      // Get recent blockhash
      const { blockhash, lastValidBlockHeight } = await this.connection.getLatestBlockhash()
      transaction.recentBlockhash = blockhash
      transaction.feePayer = wallet.publicKey

      // Sign and send
      const signedTx = await wallet.signTransaction(transaction)
      const signature = await this.connection.sendRawTransaction(signedTx.serialize())

      // Confirm transaction
      await this.connection.confirmTransaction({
        signature,
        blockhash,
        lastValidBlockHeight,
      })

      return {
        success: true,
        transactionHash: signature,
        signature,
        explorerUrl: `https://explorer.solana.com/tx/${signature}?cluster=${this.network}`,
      }
    } catch (error: any) {
      console.error("[v0] Failed to store report hash:", error)
      return {
        success: false,
        transactionHash: "",
        error: error.message || "Failed to store report hash",
      }
    }
  }

  // Verify report on blockchain
  async verifyReport(
    wallet: {
      publicKey: PublicKey
      signTransaction: (transaction: Transaction) => Promise<Transaction>
    },
    jobId: string,
    verificationData: string,
  ): Promise<TransactionResult> {
    try {
      const [reportPDA] = await this.getReportPDA(jobId, wallet.publicKey)

      // Check if report exists
      const reportAccount = await this.connection.getAccountInfo(reportPDA)
      if (!reportAccount) {
        throw new Error("Report not found on blockchain")
      }

      // Create verification transaction
      const memoProgram = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
      const verifyData = JSON.stringify({
        type: "verify_report",
        jobId,
        verificationData,
        validator: wallet.publicKey.toString(),
        timestamp: Date.now(),
      })

      const transaction = new Transaction().add({
        keys: [],
        programId: memoProgram,
        data: Buffer.from(verifyData),
      })

      const { blockhash, lastValidBlockHeight } = await this.connection.getLatestBlockhash()
      transaction.recentBlockhash = blockhash
      transaction.feePayer = wallet.publicKey

      const signedTx = await wallet.signTransaction(transaction)
      const signature = await this.connection.sendRawTransaction(signedTx.serialize())

      await this.connection.confirmTransaction({
        signature,
        blockhash,
        lastValidBlockHeight,
      })

      return {
        success: true,
        transactionHash: signature,
        signature,
        explorerUrl: `https://explorer.solana.com/tx/${signature}?cluster=${this.network}`,
      }
    } catch (error: any) {
      console.error("[v0] Failed to verify report:", error)
      return {
        success: false,
        transactionHash: "",
        error: error.message || "Failed to verify report",
      }
    }
  }

  // Get report data from blockchain
  async getReport(signature: string): Promise<ReportData | null> {
    try {
      const transaction = await this.connection.getTransaction(signature, {
        maxSupportedTransactionVersion: 0,
      })

      if (!transaction) {
        return null
      }

      // Parse memo data from transaction
      const memoInstruction = transaction.transaction.message.instructions.find((ix: any) => {
        return ix.programId.toString() === "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
      })

      if (!memoInstruction) {
        return null
      }

      const memoData = Buffer.from((memoInstruction as any).data).toString()
      const reportData = JSON.parse(memoData)

      return {
        jobId: reportData.jobId,
        reportHash: reportData.reportHash,
        reportType: reportData.reportType,
        stakeholder: reportData.stakeholder,
        metadata: reportData.metadata,
        timestamp: reportData.timestamp,
        verified: reportData.type === "verify_report",
        authority: reportData.authority,
        transactionHash: signature,
      }
    } catch (error) {
      console.error("[v0] Failed to get report:", error)
      return null
    }
  }

  // Verify transaction exists on blockchain
  async verifyTransaction(signature: string): Promise<boolean> {
    try {
      const transaction = await this.connection.getTransaction(signature, {
        maxSupportedTransactionVersion: 0,
      })
      return transaction !== null
    } catch (error) {
      console.error("[v0] Failed to verify transaction:", error)
      return false
    }
  }

  // Get storage statistics
  async getStorageStats(authority: PublicKey): Promise<StorageStats | null> {
    try {
      const [storagePDA] = await this.getReportStoragePDA(authority)
      const accountInfo = await this.connection.getAccountInfo(storagePDA)

      if (!accountInfo) {
        return null
      }

      // In a real implementation, this would decode the account data
      return {
        totalReports: 0,
        authority: authority.toString(),
        createdAt: Date.now(),
        updatedAt: Date.now(),
      }
    } catch (error) {
      console.error("[v0] Failed to get storage stats:", error)
      return null
    }
  }

  // Estimate transaction cost
  async estimateTransactionCost(): Promise<number> {
    try {
      const recentBlockhash = await this.connection.getLatestBlockhash()
      // Approximate fee in SOL (typically 5000 lamports = 0.000005 SOL)
      return 5000 / LAMPORTS_PER_SOL
    } catch (error) {
      console.error("[v0] Failed to estimate cost:", error)
      return 0.000005 // Default estimate
    }
  }

  // Get explorer URL for transaction
  getExplorerUrl(signature: string): string {
    return `https://explorer.solana.com/tx/${signature}?cluster=${this.network}`
  }

  // Get explorer URL for account
  getAccountExplorerUrl(publicKey: PublicKey): string {
    return `https://explorer.solana.com/address/${publicKey.toString()}?cluster=${this.network}`
  }
}
