"use client"

import { useEffect, useState } from "react"

interface StatsCounterProps {
  end: number
  duration?: number
  decimals?: number
}

export function StatsCounter({ end, duration = 2, decimals = 0 }: StatsCounterProps) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let startTime: number | null = null
    const startValue = 0

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime
      const progress = Math.min((currentTime - startTime) / (duration * 1000), 1)

      const currentCount = startValue + (end - startValue) * progress
      setCount(currentCount)

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [end, duration])

  return <span>{count.toFixed(decimals)}</span>
}
