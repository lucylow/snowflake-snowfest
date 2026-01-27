"use client"

import { Button } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"
import Link from "next/link"

export function FinalCTA() {
  return (
    <section className="container py-24 md:py-32">
      <div className="mx-auto max-w-4xl">
        <div className="rounded-2xl bg-primary px-8 py-16 md:px-16 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-primary-foreground mb-4 text-balance">
            Ready to transform your workflow?
          </h2>
          <p className="text-lg text-primary-foreground/90 mb-8 max-w-2xl mx-auto text-pretty leading-relaxed">
            Join thousands of teams already using SNOWFLAKE to boost productivity and streamline operations. Start your
            free trial today.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/dashboard">
              <Button size="lg" variant="secondary" className="gap-2">
                Get Started Free
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/contact">
              <Button
                size="lg"
                variant="outline"
                className="bg-transparent border-primary-foreground text-primary-foreground hover:bg-primary-foreground/10"
              >
                Schedule a Demo
              </Button>
            </Link>
          </div>
          <p className="mt-6 text-sm text-primary-foreground/80">No credit card required • Setup in minutes</p>
        </div>
      </div>
    </section>
  )
}
