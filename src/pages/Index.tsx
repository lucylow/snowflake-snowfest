import { lazy, Suspense } from "react"
import { Header } from "@/components/landing/header"
import { Hero } from "@/components/landing/hero"
import { Features } from "@/components/landing/features"
import { Footer } from "@/components/landing/footer"
import { Skeleton } from "@/components/ui/skeleton"

// Lazy load heavy components for better performance
const AlphaFoldShowcase = lazy(() =>
  import("@/components/landing/alphafold-showcase").then((mod) => ({ default: mod.AlphaFoldShowcase }))
)
const Pricing = lazy(() =>
  import("@/components/landing/pricing").then((mod) => ({ default: mod.Pricing }))
)
const Testimonials = lazy(() =>
  import("@/components/landing/testimonials").then((mod) => ({ default: mod.Testimonials }))
)
const FinalCTA = lazy(() =>
  import("@/components/landing/final-cta").then((mod) => ({ default: mod.FinalCTA }))
)

// Loading fallback component
const SectionSkeleton = () => (
  <div className="container py-24">
    <Skeleton className="h-12 w-64 mx-auto mb-8" />
    <div className="grid gap-6 md:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-64" />
      ))}
    </div>
  </div>
)

const Index = () => {
  // Smooth scroll handler for hash links
  const handleHashClick = (e: React.MouseEvent<HTMLAnchorElement>, hash: string) => {
    e.preventDefault()
    const element = document.querySelector(hash)
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Hero />
        <Features />
        <Suspense fallback={<SectionSkeleton />}>
          <AlphaFoldShowcase />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <Testimonials />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <Pricing />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <FinalCTA />
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}

export default Index
