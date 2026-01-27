"use client"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, XCircle, WifiOff } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ErrorAlertProps {
  title?: string
  message: string
  onRetry?: () => void
  variant?: "default" | "destructive"
}

export function ErrorAlert({ title = "Error", message, onRetry, variant = "destructive" }: ErrorAlertProps) {
  const getIcon = () => {
    if (message.includes("network") || message.includes("connect")) {
      return <WifiOff className="h-4 w-4" />
    }
    if (variant === "destructive") {
      return <XCircle className="h-4 w-4" />
    }
    return <AlertCircle className="h-4 w-4" />
  }

  return (
    <Alert variant={variant}>
      {getIcon()}
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex items-center justify-between gap-4">
        <span>{message}</span>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}
