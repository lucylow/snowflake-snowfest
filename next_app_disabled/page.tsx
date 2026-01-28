import { Header } from "@/components/landing/header"
import { Hero } from "@/components/landing/hero"
import { Features } from "@/components/landing/features"
import { Testimonials } from "@/components/landing/testimonials"
import { Pricing } from "@/components/landing/pricing"
import { FinalCTA } from "@/components/landing/final-cta"
import { Footer } from "@/components/landing/footer"
import { StatsCounter } from "@/components/landing/stats-counter"
import { InteractiveDemo } from "@/components/landing/interactive-demo"
import { AIDemo } from "@/components/landing/ai-demo"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent } from "@/components/ui/card"
import { PlayCircle, Brain, Eye, CheckCircle, Cpu, Dna } from "lucide-react"
import { AlphaFoldShowcase } from "@/components/landing/alphafold-showcase"
import { HealthImpact } from "@/components/landing/health-impact"

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <Hero />

        <section className="py-12 sm:py-16 bg-muted/30">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8">
              <div className="text-center">
                <div className="text-3xl sm:text-4xl font-bold text-primary mb-2">
                  <StatsCounter end={15420} duration={2} />+
                </div>
                <div className="text-sm sm:text-base text-muted-foreground">Proteins Analyzed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl sm:text-4xl font-bold text-green-500 mb-2">
                  <StatsCounter end={2.3} duration={2} decimals={1} />M
                </div>
                <div className="text-sm sm:text-base text-muted-foreground">Compounds Screened</div>
              </div>
              <div className="text-center">
                <div className="text-3xl sm:text-4xl font-bold text-purple-500 mb-2">
                  <StatsCounter end={500} duration={2} />+
                </div>
                <div className="text-sm sm:text-base text-muted-foreground">Disease Targets</div>
              </div>
              <div className="text-center">
                <div className="text-3xl sm:text-4xl font-bold text-blue-500 mb-2">
                  <StatsCounter end={91} duration={2} />%
                </div>
                <div className="text-sm sm:text-base text-muted-foreground">AI Confidence</div>
              </div>
            </div>
          </div>
        </section>

        <Features />

        <AlphaFoldShowcase />

        <HealthImpact />

        <section id="how-it-works" className="py-16 sm:py-20 lg:py-24 bg-muted/30">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
            <div className="text-center mb-12 sm:mb-16">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6">How It Works</h2>
              <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto">
                From protein sequence to therapeutic insights in three simple steps
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 sm:gap-8 max-w-6xl mx-auto">
              <Card className="text-center border-border">
                <CardContent className="p-6 sm:p-8">
                  <div className="w-14 h-14 sm:w-16 sm:h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <Dna className="w-7 h-7 sm:w-8 sm:h-8 text-primary" />
                  </div>
                  <h3 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4">1. Input Sequence or Structure</h3>
                  <p className="text-sm sm:text-base text-muted-foreground">
                    Paste protein sequence for AlphaFold prediction, or upload PDB structure. Add ligand file for
                    docking screening.
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center border-border">
                <CardContent className="p-6 sm:p-8">
                  <div className="w-14 h-14 sm:w-16 sm:h-16 bg-purple-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <Cpu className="w-7 h-7 sm:w-8 sm:h-8 text-purple-500" />
                  </div>
                  <h3 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4">2. AI Structure & Docking</h3>
                  <p className="text-sm sm:text-base text-muted-foreground">
                    AlphaFold predicts 3D structure with confidence scores. GPU-accelerated AutoDock Vina screens
                    binding poses.
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center border-border">
                <CardContent className="p-6 sm:p-8">
                  <div className="w-14 h-14 sm:w-16 sm:h-16 bg-green-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <Brain className="w-7 h-7 sm:w-8 sm:h-8 text-green-500" />
                  </div>
                  <h3 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4">3. AI Analysis & Insights</h3>
                  <p className="text-sm sm:text-base text-muted-foreground">
                    Get ML-powered ADMET predictions, drug-likeness scores, and stakeholder-specific therapeutic
                    recommendations.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        <section id="demo" className="py-16 sm:py-20 lg:py-24">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
            <div className="text-center mb-12 sm:mb-16">
              <Badge className="mb-4 sm:mb-6">Interactive Demo</Badge>
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6">
                Experience SNOWFLAKE in Action
              </h2>
              <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto">
                Explore AI-powered drug discovery with real protein-ligand examples. No registration required.
              </p>
            </div>

            <Tabs defaultValue="ai" className="max-w-6xl mx-auto">
              <TabsList className="grid w-full grid-cols-3 mb-8">
                <TabsTrigger value="ai" className="gap-2 text-sm sm:text-base">
                  <Brain className="w-4 h-4" />
                  AI Analysis
                </TabsTrigger>
                <TabsTrigger value="interactive" className="gap-2 text-sm sm:text-base">
                  <PlayCircle className="w-4 h-4" />
                  <span className="hidden sm:inline">Interactive</span> Demo
                </TabsTrigger>
                <TabsTrigger value="visualization" className="gap-2 text-sm sm:text-base">
                  <Eye className="w-4 h-4" />
                  <span className="hidden sm:inline">3D</span> Viz
                </TabsTrigger>
              </TabsList>

              <TabsContent value="ai">
                <AIDemo />
              </TabsContent>

              <TabsContent value="interactive">
                <InteractiveDemo />
              </TabsContent>

              <TabsContent value="visualization">
                <Card className="border-border">
                  <CardContent className="p-6 sm:p-8">
                    <div className="grid lg:grid-cols-2 gap-8">
                      <div>
                        <h3 className="text-xl sm:text-2xl font-bold mb-4">3D Molecular Viewer</h3>
                        <p className="text-muted-foreground mb-6">
                          Explore protein-ligand interactions in real-time with our interactive 3D viewer powered by
                          WebGL.
                        </p>
                        <ul className="space-y-3">
                          <li className="flex items-center gap-3">
                            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                            <span className="text-sm sm:text-base">Real-time rotation and zoom</span>
                          </li>
                          <li className="flex items-center gap-3">
                            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                            <span className="text-sm sm:text-base">Hydrogen bond visualization</span>
                          </li>
                          <li className="flex items-center gap-3">
                            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                            <span className="text-sm sm:text-base">
                              Multiple rendering styles (cartoon, surface, sticks)
                            </span>
                          </li>
                          <li className="flex items-center gap-3">
                            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                            <span className="text-sm sm:text-base">Export publication-quality images</span>
                          </li>
                        </ul>
                      </div>

                      <div className="h-64 sm:h-80 bg-muted rounded-lg flex items-center justify-center">
                        <div className="text-center">
                          <Eye className="w-12 h-12 text-primary mx-auto mb-4" />
                          <p className="text-muted-foreground">Interactive 3D visualization</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </section>

        <Testimonials />
        <Pricing />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  )
}
