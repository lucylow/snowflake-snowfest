# Solana Blockchain Integration

Complete guide for the Solana blockchain integration in SNOWFLAKE's molecular docking platform.

## Overview

SNOWFLAKE uses Solana blockchain to provide immutable, verifiable storage of molecular docking reports. This ensures data integrity, creates audit trails, and enables trustless verification for research papers, grant applications, and regulatory submissions.

## Features

### 1. **Report Storage on Blockchain**
- Cryptographic SHA-256 hashing of report content
- Immutable storage on Solana blockchain
- Comprehensive metadata including job ID, report type, stakeholder, and timestamp
- Low transaction costs (~0.000005 SOL per transaction)

### 2. **Phantom Wallet Integration**
- Seamless connection to Phantom wallet
- Real-time balance tracking
- Transaction signing and confirmation
- Wallet address display and management

### 3. **Advanced SDK (SnowflakeSDK)**
- Complete TypeScript SDK for blockchain operations
- Program Derived Address (PDA) generation
- Transaction cost estimation
- Multi-network support (devnet, testnet, mainnet)
- Report verification and retrieval

### 4. **Blockchain Verification**
- Verify any transaction signature
- Retrieve complete report metadata
- View transaction details on Solana Explorer
- Tamper-proof audit trail

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Report     │  │   Wallet     │  │  Blockchain  │    │
│  │  Generator   │  │   Context    │  │    Page      │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                               │
└────────────────────────────┼───────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  SolanaClient   │
                    │  + SDK Layer    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Solana Network  │
                    │   (Blockchain)  │
                    └─────────────────┘
```

## Setup Instructions

### 1. Install Phantom Wallet
Download and install Phantom wallet from [phantom.app](https://phantom.app)

### 2. Environment Configuration
Add the following to your `.env.local` file:

```bash
# Solana Configuration
NEXT_PUBLIC_SOLANA_NETWORK=devnet  # devnet, testnet, or mainnet-beta
```

### 3. Get Devnet SOL
For testing on devnet:
1. Connect your wallet on the Blockchain page
2. Click "Request Airdrop (Devnet)" to get 1 SOL
3. Use the SOL for transaction fees

## Usage Guide

### Storing Reports on Blockchain

```typescript
import { solanaClient } from "@/lib/solana-client"
import { useWallet } from "@/contexts/wallet-context"

// In your component
const { wallet, connected } = useWallet()

// Store a report
const result = await solanaClient.storeReportWithSDK(wallet, {
  jobId: "job_123",
  reportContent: reportHtmlContent,
  reportType: "html",
  stakeholder: "researcher",
  metadata: {
    includeVisualizations: true,
    version: "2.0"
  }
})

if (result.success) {
  console.log("Transaction signature:", result.signature)
  console.log("Explorer URL:", result.explorerUrl)
}
```

### Verifying Reports

```typescript
// Get report data from transaction
const reportData = await solanaClient.getReportData(signature)

if (reportData) {
  console.log("Job ID:", reportData.jobId)
  console.log("Report Hash:", reportData.reportHash)
  console.log("Stakeholder:", reportData.stakeholder)
  console.log("Verified:", reportData.verified)
}
```

### Using the SNOWFLAKE SDK Directly

```typescript
import { SnowflakeSDK } from "@/lib/solana/snowflake-sdk"
import { Connection } from "@solana/web3.js"

const connection = new Connection("https://api.devnet.solana.com")
const sdk = new SnowflakeSDK(connection, "devnet")

// Generate report hash
const hash = sdk.generateReportHash(reportContent)

// Get estimated cost
const cost = await sdk.estimateTransactionCost()

// Store report
const result = await sdk.storeReportHash(wallet, {
  jobId: "job_123",
  reportContent: reportContent,
  reportType: "pdf",
  stakeholder: "investor",
  metadata: { version: "1.0" }
})
```

## API Reference

### SolanaClient Methods

#### `getBalance(publicKey: PublicKey): Promise<number>`
Get wallet balance in SOL.

#### `storeReportWithSDK(wallet, params): Promise<TransactionResult>`
Store a report hash on blockchain with comprehensive metadata.

**Parameters:**
- `wallet`: Phantom wallet instance
- `params.jobId`: Unique job identifier (max 64 chars)
- `params.reportContent`: Report content (string or Buffer)
- `params.reportType`: Report format (max 32 chars)
- `params.stakeholder`: Target audience (max 32 chars)
- `params.metadata`: Additional metadata (max 512 chars when stringified)

**Returns:**
```typescript
{
  success: boolean
  transactionHash: string
  signature?: string
  error?: string
  explorerUrl?: string
}
```

#### `verifyReportWithSDK(wallet, jobId, verificationData): Promise<TransactionResult>`
Verify a stored report on blockchain.

#### `getReportData(signature: string): Promise<ReportData | null>`
Retrieve complete report data from a transaction signature.

#### `requestAirdrop(publicKey: PublicKey, amount: number): Promise<string>`
Request SOL airdrop on devnet/testnet (not available on mainnet).

### SnowflakeSDK Methods

#### `generateReportHash(content: string | Buffer): string`
Generate SHA-256 hash of report content.

#### `estimateTransactionCost(): Promise<number>`
Estimate transaction cost in SOL (typically ~0.000005 SOL).

#### `getExplorerUrl(signature: string): string`
Get Solana Explorer URL for a transaction.

#### `getAccountExplorerUrl(publicKey: PublicKey): string`
Get Solana Explorer URL for an account.

## Security Considerations

### 1. **Cryptographic Hashing**
All reports are hashed using SHA-256 before blockchain storage, ensuring:
- Content integrity verification
- Tamper detection
- Privacy (only hash is stored on-chain)

### 2. **Transaction Signing**
All blockchain transactions require wallet signature:
- User explicitly approves each transaction
- Private keys never leave Phantom wallet
- Transaction details visible before signing

### 3. **Immutability**
Once stored on Solana blockchain:
- Data cannot be altered or deleted
- Complete audit trail available
- Verifiable by anyone at any time

### 4. **Network Selection**
- **Devnet**: For development and testing
- **Testnet**: For staging and integration testing
- **Mainnet**: For production use (requires real SOL)

## Best Practices

### 1. **Report Storage**
- Always store critical reports on blockchain
- Include comprehensive metadata
- Keep transaction signatures for future verification
- Use stakeholder-specific report types

### 2. **Verification**
- Verify transaction confirmation before proceeding
- Store transaction signatures in your database
- Provide users with Explorer links
- Implement retry logic for failed transactions

### 3. **Cost Management**
- Estimate transaction costs before execution
- Maintain sufficient balance for operations
- Batch operations when possible
- Monitor network fees on mainnet

### 4. **Error Handling**
- Handle wallet connection errors gracefully
- Provide clear error messages to users
- Implement transaction timeout logic
- Retry failed transactions with exponential backoff

## Troubleshooting

### Wallet Not Connecting
- Ensure Phantom wallet is installed
- Check if wallet is unlocked
- Verify network selection matches app configuration
- Try refreshing the page

### Transaction Failures
- Check wallet balance is sufficient
- Verify network is not congested
- Ensure inputs are within size limits
- Try again after a few seconds

### Verification Issues
- Confirm transaction signature is correct
- Check network selection matches transaction network
- Wait for transaction confirmation (typically 1-2 seconds)
- Use Solana Explorer to manually verify

## Cost Analysis

### Devnet/Testnet
- **Transaction Cost**: ~0.000005 SOL (free from airdrops)
- **Airdrop Available**: Yes, 1 SOL per request
- **Ideal For**: Development, testing, demos

### Mainnet
- **Transaction Cost**: ~0.000005 SOL (~$0.0001 USD at $20/SOL)
- **Airdrop Available**: No
- **Ideal For**: Production, real reports

## Stakeholder Benefits

### For Researchers
- Immutable proof of research timeline
- Verifiable data for publications
- Transparent methodology documentation
- Grant application support

### For Investors
- Transparent progress tracking
- Verifiable milestone completion
- Due diligence support
- Risk assessment data

### For Regulators
- Complete audit trail
- Tamper-proof documentation
- Compliance verification
- Historical data access

### For Clinicians
- Patient safety verification
- Treatment efficacy tracking
- Clinical trial documentation
- Regulatory submission support

## Network Endpoints

### Devnet
- RPC: `https://api.devnet.solana.com`
- Explorer: `https://explorer.solana.com/?cluster=devnet`

### Testnet
- RPC: `https://api.testnet.solana.com`
- Explorer: `https://explorer.solana.com/?cluster=testnet`

### Mainnet
- RPC: `https://api.mainnet-beta.solana.com`
- Explorer: `https://explorer.solana.com/`

## Support

For issues or questions:
1. Check transaction on Solana Explorer
2. Review browser console for error logs
3. Verify wallet connection and balance
4. Contact support with transaction signature

## Future Enhancements

Planned features:
- Multi-signature verification
- Batch report storage
- Advanced metadata search
- Report versioning on-chain
- NFT generation for milestone reports
- DAO governance for validation
