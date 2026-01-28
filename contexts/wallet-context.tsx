"use client"

import type React from "react"
import { createContext, useContext, useEffect, useState, useCallback } from "react"
import type { PublicKey, Transaction } from "@solana/web3.js"

interface PhantomWallet {
  publicKey: PublicKey
  isConnected?: boolean
  signTransaction: (transaction: Transaction) => Promise<Transaction>
  signAllTransactions: (transactions: Transaction[]) => Promise<Transaction[]>
  connect: () => Promise<{ publicKey: PublicKey }>
  disconnect: () => Promise<void>
  on?: (event: string, callback: (arg: unknown) => void) => void
  removeAllListeners?: () => void
}

interface WalletContextType {
  wallet: PhantomWallet | null
  publicKey: PublicKey | null
  connected: boolean
  connecting: boolean
  connect: () => Promise<void>
  disconnect: () => Promise<void>
  error: string | null
}

const WalletContext = createContext<WalletContextType | undefined>(undefined)

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [wallet, setWallet] = useState<PhantomWallet | null>(null)
  const [publicKey, setPublicKey] = useState<PublicKey | null>(null)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const getPhantomWallet = useCallback((): PhantomWallet | null => {
    if (typeof window === "undefined") return null

    try {
      const { solana } = window as { solana?: PhantomWallet }
      if (solana?.isPhantom) {
        return solana
      }
    } catch (err) {
      console.warn("[v0] Could not access Phantom wallet:", err)
    }
    return null
  }, [])

  // Connect wallet
  const connect = useCallback(async () => {
    setError(null)
    setConnecting(true)

    try {
      const phantomWallet = getPhantomWallet()

      if (!phantomWallet) {
        throw new Error("Phantom wallet not found. Install from phantom.app (optional)")
      }

      const response = await phantomWallet.connect()
      setWallet(phantomWallet)
      setPublicKey(response.publicKey)
      setConnected(true)
    } catch (err: unknown) {
      console.info("[v0] Wallet connection optional:", err.message)
      setError(err.message || "Wallet connection optional")
      setConnected(false)
    } finally {
      setConnecting(false)
    }
  }, [getPhantomWallet])

  // Disconnect wallet
  const disconnect = useCallback(async () => {
    try {
      if (wallet) {
        await wallet.disconnect()
      }
      setWallet(null)
      setPublicKey(null)
      setConnected(false)
      setError(null)
    } catch (err: unknown) {
      console.warn("[v0] Disconnect failed:", err)
    }
  }, [wallet])

  useEffect(() => {
    const phantomWallet = getPhantomWallet()

    if (phantomWallet) {
      try {
        phantomWallet.on?.("connect", (publicKey: PublicKey) => {
          setWallet(phantomWallet)
          setPublicKey(publicKey)
          setConnected(true)
        })

        phantomWallet.on?.("disconnect", () => {
          setWallet(null)
          setPublicKey(null)
          setConnected(false)
        })

        if (phantomWallet.isConnected) {
          setWallet(phantomWallet)
          setPublicKey(phantomWallet.publicKey)
          setConnected(true)
        }
      } catch (err) {
        console.warn("[v0] Wallet listener setup failed:", err)
      }
    }

    return () => {
      if (phantomWallet) {
        try {
          phantomWallet.removeAllListeners?.()
        } catch (err) {
          // Ignore cleanup errors
        }
      }
    }
  }, [getPhantomWallet])

  return (
    <WalletContext.Provider
      value={{
        wallet,
        publicKey,
        connected,
        connecting,
        connect,
        disconnect,
        error,
      }}
    >
      {children}
    </WalletContext.Provider>
  )
}

export function useWallet() {
  const context = useContext(WalletContext)
  if (context === undefined) {
    throw new Error("useWallet must be used within a WalletProvider")
  }
  return context
}
