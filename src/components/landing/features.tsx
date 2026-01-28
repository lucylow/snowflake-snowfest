import { Card, CardContent } from "@/components/ui/card"
import { 
  Dna, 
  Zap, 
  Brain, 
  Cpu, 
  BarChart3, 
  Shield, 
  FileText, 
  Eye,
  Activity,
  TrendingUp
} from "lucide-react"

const features = [
  {
    icon: Dna,
    title: "AlphaFold Structure Prediction",
    description: "Transform amino acid sequences into accurate 3D protein structures with atomic-level precision using DeepMind's AlphaFold",
    metric: "91% avg confidence",
    highlight: "Industry-leading accuracy",
  },
  {
    icon: Cpu,
    title: "GPU-Accelerated Docking",
    description: "Lightning-fast molecular docking powered by Gnina GPU acceleration. Process multiple ligands in parallel for rapid screening",
    metric: "10-100x faster",
    highlight: "Parallel processing",
  },
  {
    icon: BarChart3,
    title: "Advanced Statistics & Clustering",
    description: "Comprehensive statistical analysis with pose clustering, confidence intervals, outlier detection, and quality metrics",
    metric: "15+ metrics",
    highlight: "Data-driven insights",
  },
  {
    icon: Activity,
    title: "ADMET Predictions",
    description: "Complete absorption, distribution, metabolism, excretion, and toxicity analysis with ML-powered property predictions",
    metric: "20+ properties",
    highlight: "Clinical relevance",
  },
  {
    icon: Shield,
    title: "Toxicity Assessment",
    description: "Comprehensive safety profiling including LD50, hepatotoxicity, mutagenicity, carcinogenicity, and hERG inhibition",
    metric: "8 risk factors",
    highlight: "Safety first",
  },
  {
    icon: Brain,
    title: "AI-Powered Drug-Likeness",
    description: "ML analysis using Lipinski's Rule, QED scores, Veber's Rule, and synthetic accessibility for optimal drug candidates",
    metric: "98.3% accuracy",
    highlight: "ML-validated",
  },
  {
    icon: FileText,
    title: "Stakeholder-Specific Reports",
    description: "Tailored analysis reports for researchers, investors, regulators, and clinicians with targeted insights",
    metric: "4 report types",
    highlight: "Context-aware",
  },
  {
    icon: Eye,
    title: "3D Molecular Visualization",
    description: "Interactive 3D protein-ligand structure viewing with pose analysis, binding site exploration, and real-time manipulation",
    metric: "Real-time rendering",
    highlight: "Immersive experience",
  },
  {
    icon: TrendingUp,
    title: "Blockchain Verification",
    description: "Immutable report storage on Solana blockchain with cryptographic verification and tamper-proof audit trails",
    metric: "~$0.00001 per report",
    highlight: "Trust & transparency",
  },
]

export function Features() {
  return (
    <section id="features" className="bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 sm:py-32 md:py-40">
        <div className="text-center mb-16 sm:mb-20">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl mb-4 sm:mb-6 text-balance">
            Complete AI Platform for Drug Discovery
          </h2>
          <p className="text-base text-muted-foreground sm:text-lg md:text-xl max-w-2xl mx-auto text-pretty leading-relaxed">
            From protein sequence to drug candidate analysis—powered by cutting-edge AI, GPU acceleration, and blockchain verification
          </p>
        </div>

        <div className="grid gap-6 sm:gap-8 md:grid-cols-2 lg:grid-cols-3 lg:gap-10">
          {features.map((feature, index) => (
            <Card 
              key={index} 
              className="border-2 hover:border-primary/50 hover:shadow-xl transition-all duration-300 group relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <CardContent className="p-8 relative">
                <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="h-7 w-7 text-primary" />
                </div>
                <div className="mb-2">
                  <span className="text-xs font-semibold text-primary/70 uppercase tracking-wide">
                    {feature.highlight}
                  </span>
                </div>
                <h3 className="text-xl md:text-2xl font-semibold mb-3 group-hover:text-primary transition-colors">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed text-base mb-4">
                  {feature.description}
                </p>
                <div className="flex items-baseline gap-2">
                  <div className="text-2xl font-bold text-primary">{feature.metric}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
