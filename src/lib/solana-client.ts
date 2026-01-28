import { Connection, LAMPORTS_PER_SOL, PublicKey, SystemProgram, Transaction } from "@solana/web3.js"

import { CURRENT_NETWORK, LOG_PREFIX, SOLANA_NETWORKS } from "./constants"
import { SnowflakeSDK } from "./solana/snowflake-sdk"

const RPC_URL = SOLANA_NETWORKS[CURRENT_NETWORK]?.rpc ?? SOLANA_NETWORKS.devnet.rpc

export class SolanaClient {
  private connection: Connection
  private snowflakeSDK: SnowflakeSDK | null = null

  constructor() {
    this.connection = new Connection(RPC_URL, "confirmed")
  }

  // Get connection object
  getConnection() {
    return this.connection
  }

  // Get wallet balance in SOL
  async getBalance(publicKey: PublicKey): Promise<number> {
    if (!publicKey) {
      throw new Error("Public key is required")
    }

    try {
      const balance = await this.connection.getBalance(publicKey)
      if (balance < 0) {
        throw new Error("Invalid balance returned from Solana")
      }
      return balance / LAMPORTS_PER_SOL
    } catch (error) {
      console.error(`${LOG_PREFIX} Error fetching balance:`, error)
      const errorMessage = error instanceof Error ? error.message : "Unknown error"
      if (errorMessage.includes("timeout") || errorMessage.includes("network")) {
        throw new Error("Network error connecting to Solana. Please check your connection.")
      }
      throw new Error(`Failed to fetch wallet balance: ${errorMessage}`)
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
    if (!wallet || !wallet.publicKey) {
      throw new Error("Wallet is required")
    }

    if (!dataHash || !dataHash.trim()) {
      throw new Error("Data hash is required")
    }

    try {
      // Create a memo instruction with the data hash
      const memoProgram = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

      const memoData = JSON.stringify({
        type: "molecular_docking_report",
        hash: dataHash,
        timestamp: Date.now(),
        metadata: metadata || "",
      })

      if (memoData.length > 1232) {
        throw new Error("Memo data too long (Solana limit: 1232 bytes)")
      }

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

      // Get recent blockhash with timeout
      let blockhash: string
      let lastValidBlockHeight: number
      try {
        const blockhashResult = await Promise.race([
          this.connection.getLatestBlockhash(),
          new Promise<never>((_, reject) => 
            setTimeout(() => reject(new Error("Timeout getting blockhash")), 10000)
          )
        ])
        blockhash = blockhashResult.blockhash
        lastValidBlockHeight = blockhashResult.lastValidBlockHeight
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error"
        throw new Error(`Failed to get recent blockhash: ${errorMessage}`)
      }

      transaction.recentBlockhash = blockhash
      transaction.feePayer = wallet.publicKey

      // Sign and send transaction
      let signedTransaction: Transaction
      try {
        signedTransaction = await wallet.signTransaction(transaction)
      } catch (error) {
        throw new Error(`Failed to sign transaction: ${error instanceof Error ? error.message : String(error)}`)
      }

      let signature: string
      try {
        signature = await this.connection.sendRawTransaction(signedTransaction.serialize(), {
          skipPreflight: false,
          maxRetries: 3,
        })
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error"
        throw new Error(`Failed to send transaction: ${errorMessage}`)
      }

      // Confirm transaction with timeout
      try {
        await Promise.race([
          this.connection.confirmTransaction({
            signature,
            blockhash,
            lastValidBlockHeight,
          }),
          new Promise<never>((_, reject) => 
            setTimeout(() => reject(new Error("Transaction confirmation timeout")), 30000)
          )
        ])
      } catch (error) {
        // Transaction may still be confirmed even if confirmation times out
        console.warn("[v0] Transaction confirmation timeout or error:", error)
      }

      return signature
    } catch (error) {
      console.error(`${LOG_PREFIX} Error storing data on blockchain:`, error)
      const errorMessage = error instanceof Error ? error.message : "Unknown error"
      throw new Error(`Failed to store data on blockchain: ${errorMessage}`)
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
      console.error(`${LOG_PREFIX} Error verifying data:`, error)
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
      console.error(`${LOG_PREFIX} Error fetching transaction:`, error)
      throw new Error("Failed to fetch transaction details")
    }
  }

  // Airdrop SOL (devnet/testnet only)
  async requestAirdrop(publicKey: PublicKey, amount = 1): Promise<string> {
    try {
      if (CURRENT_NETWORK === "mainnet") {
        throw new Error("Airdrop not available on mainnet")
      }

      const signature = await this.connection.requestAirdrop(publicKey, amount * LAMPORTS_PER_SOL)

      await this.connection.confirmTransaction(signature)
      return signature
    } catch (error) {
      console.error(`${LOG_PREFIX} Error requesting airdrop:`, error)
      throw new Error("Failed to request airdrop")
    }
  }

  getSnowflakeSDK(): SnowflakeSDK {
    if (!this.snowflakeSDK) {
      this.snowflakeSDK = new SnowflakeSDK(this.connection, CURRENT_NETWORK)
    }
    return this.snowflakeSDK
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
    const sdk = this.getSnowflakeSDK()
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
    const sdk = this.getSnowflakeSDK()
    return sdk.verifyReport(wallet, jobId, verificationData)
  }

  async getReportData(signature: string) {
    const sdk = this.getSnowflakeSDK()
    return sdk.getReport(signature)
  }
}

export const solanaClient = new SolanaClient()
