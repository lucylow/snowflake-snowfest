import { Connection, PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js"
import { NeuravivaSDK } from "./solana/neuraviva-sdk"

// Solana network configuration
const NETWORK = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet"
const RPC_URL =
  NETWORK === "mainnet-beta"
    ? "https://api.mainnet-beta.solana.com"
    : NETWORK === "testnet"
      ? "https://api.testnet.solana.com"
      : "https://api.devnet.solana.com"

export class SolanaClient {
  private connection: Connection
  private neuravivaSDK: NeuravivaSDK | null = null

  constructor() {
    this.connection = new Connection(RPC_URL, "confirmed")
  }

  // Get connection object
  getConnection() {
    return this.connection
  }

  // Get wallet balance in SOL
  async getBalance(publicKey: PublicKey): Promise<number> {
    try {
      const balance = await this.connection.getBalance(publicKey)
      return balance / LAMPORTS_PER_SOL
    } catch (error) {
      console.error("[v0] Error fetching balance:", error)
      throw new Error("Failed to fetch wallet balance")
    }
  }

  // Store data hash on-chain
  async storeDataHash(
    wallet: {
      publicKey: PublicKey
      signTransaction: (transaction: Transaction) => Promise<Transaction>
    },
    dataHash: string,
    metadata?: string,
  ): Promise<string> {
    try {
      // Create a memo instruction with the data hash
      const memoProgram = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

      const memoData = JSON.stringify({
        type: "molecular_docking_report",
        hash: dataHash,
        timestamp: Date.now(),
        metadata: metadata || "",
      })

      // Create transaction
      const transaction = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: wallet.publicKey,
          toPubkey: wallet.publicKey, // Send to self
          lamports: 1, // Minimal amount
        }),
      )

      // Add memo instruction
      transaction.add({
        keys: [],
        programId: memoProgram,
        data: Buffer.from(memoData),
      })

      // Get recent blockhash
      const { blockhash, lastValidBlockHeight } = await this.connection.getLatestBlockhash()
      transaction.recentBlockhash = blockhash
      transaction.feePayer = wallet.publicKey

      // Sign and send transaction
      const signedTransaction = await wallet.signTransaction(transaction)
      const signature = await this.connection.sendRawTransaction(signedTransaction.serialize())

      // Confirm transaction
      await this.connection.confirmTransaction({
        signature,
        blockhash,
        lastValidBlockHeight,
      })

      return signature
    } catch (error) {
      console.error("[v0] Error storing data on blockchain:", error)
      throw new Error("Failed to store data on blockchain")
    }
  }

  // Verify data exists on-chain
  async verifyDataHash(signature: string): Promise<boolean> {
    try {
      const transaction = await this.connection.getTransaction(signature, {
        maxSupportedTransactionVersion: 0,
      })
      return transaction !== null
    } catch (error) {
      console.error("[v0] Error verifying data:", error)
      return false
    }
  }

  // Get transaction details
  async getTransactionDetails(signature: string) {
    try {
      const transaction = await this.connection.getTransaction(signature, {
        maxSupportedTransactionVersion: 0,
      })
      return transaction
    } catch (error) {
      console.error("[v0] Error fetching transaction:", error)
      throw new Error("Failed to fetch transaction details")
    }
  }

  // Airdrop SOL (devnet/testnet only)
  async requestAirdrop(publicKey: PublicKey, amount = 1): Promise<string> {
    try {
      if (NETWORK === "mainnet-beta") {
        throw new Error("Airdrop not available on mainnet")
      }

      const signature = await this.connection.requestAirdrop(publicKey, amount * LAMPORTS_PER_SOL)

      await this.connection.confirmTransaction(signature)
      return signature
    } catch (error) {
      console.error("[v0] Error requesting airdrop:", error)
      throw new Error("Failed to request airdrop")
    }
  }

  getNeuravivaSDK(): NeuravivaSDK {
    if (!this.neuravivaSDK) {
      this.neuravivaSDK = new NeuravivaSDK(this.connection, NETWORK)
    }
    return this.neuravivaSDK
  }

  async storeReportWithSDK(
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
  ) {
    const sdk = this.getNeuravivaSDK()
    return sdk.storeReportHash(wallet, params)
  }

  async verifyReportWithSDK(
    wallet: {
      publicKey: PublicKey
      signTransaction: (transaction: Transaction) => Promise<Transaction>
    },
    jobId: string,
    verificationData: string,
  ) {
    const sdk = this.getNeuravivaSDK()
    return sdk.verifyReport(wallet, jobId, verificationData)
  }

  async getReportData(signature: string) {
    const sdk = this.getNeuravivaSDK()
    return sdk.getReport(signature)
  }
}

export const solanaClient = new SolanaClient()
