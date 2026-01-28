
import { Button } from "@/components/ui/button"
import { ArrowRight, Play } from "lucide-react"
import { Link } from "react-router-dom"

export function Hero() {
  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 sm:py-32 md:py-40 lg:py-48">
      <div className="mx-auto max-w-4xl text-center">
        <div className="mb-8 inline-flex items-center rounded-full border bg-muted px-4 py-2 text-sm shadow-sm sm:px-5">
          <span className="mr-3 h-2 w-2 rounded-full bg-primary animate-pulse"></span>
          New: AI-Powered AlphaFold Structure Prediction
        </div>

        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl mb-6 sm:mb-8 text-balance leading-tight">
          Accelerate Drug Discovery with AI-Powered Molecular Docking
        </h1>

        <p className="mx-auto max-w-2xl text-base text-muted-foreground sm:text-lg md:text-xl mb-10 sm:mb-12 text-pretty leading-relaxed">
          Transform protein sequences into drug candidates using AlphaFold structure prediction, GPU-accelerated
          docking, and AI analysis. From sequence to insight in minutes.
        </p>

        <div className="flex flex-col gap-4 justify-center items-center mb-8 sm:flex-row">
          <Link to="/dashboard">
            <Button size="lg" className="gap-2 text-base">
              Start Free Trial
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <a
            href="#features"
            onClick={(e) => {
              e.preventDefault()
              document.querySelector("#features")?.scrollIntoView({ behavior: "smooth" })
            }}
          >
            <Button size="lg" variant="outline" className="gap-2 text-base bg-transparent">
              <Play className="h-4 w-4" />
              Watch Demo
            </Button>
          </a>
        </div>

        <p className="mt-6 text-sm text-muted-foreground sm:mt-8">
          No credit card required • 14-day free trial • 100 free predictions
        </p>
      </div>
    </section>
  )
}
