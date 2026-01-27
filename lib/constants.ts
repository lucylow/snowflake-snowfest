// Application constants

export const APP_NAME = "SNOWFLAKE"
export const APP_DESCRIPTION = "Advanced Molecular Docking Platform with AI Analysis and Blockchain Verification"
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://snowflake.com"

// Solana Configuration
export const SOLANA_NETWORKS = {
  devnet: {
    name: "Devnet",
    rpc: "https://api.devnet.solana.com",
    explorer: "https://explorer.solana.com/?cluster=devnet",
  },
  testnet: {
    name: "Testnet",
    rpc: "https://api.testnet.solana.com",
    explorer: "https://explorer.solana.com/?cluster=testnet",
  },
  mainnet: {
    name: "Mainnet Beta",
    rpc: "https://api.mainnet-beta.solana.com",
    explorer: "https://explorer.solana.com/",
  },
} as const

export const CURRENT_NETWORK = (process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet") as keyof typeof SOLANA_NETWORKS

// Transaction Configuration
export const TRANSACTION_TIMEOUT = 30000 // 30 seconds
export const CONFIRMATION_COMMITMENT = "confirmed"
export const ESTIMATED_TX_COST = 0.000005 // SOL

// Report Configuration
export const REPORT_TYPES = ["pdf", "html", "json", "docx", "markdown"] as const
export const STAKEHOLDER_TYPES = ["researcher", "investor", "regulator", "clinician"] as const

export const STAKEHOLDER_INFO = {
  researcher: {
    label: "Researcher",
    description: "Technical, method-focused",
    icon: "microscope",
  },
  investor: {
    label: "Investor",
    description: "Business, ROI-focused",
    icon: "trending-up",
  },
  regulator: {
    label: "Regulator",
    description: "Compliance, safety-focused",
    icon: "shield-check",
  },
  clinician: {
    label: "Clinician",
    description: "Patient, therapeutic-focused",
    icon: "heart-pulse",
  },
} as const

// AI Analysis Configuration
export const ANALYSIS_TYPES = {
  binding_affinity: {
    label: "Binding Affinity",
    description: "Analyze protein-ligand binding strength",
    estimatedCost: 0.05,
  },
  drug_likeness: {
    label: "Drug-Likeness",
    description: "Evaluate pharmaceutical properties",
    estimatedCost: 0.03,
  },
  toxicity: {
    label: "Toxicity Assessment",
    description: "Predict potential toxic effects",
    estimatedCost: 0.04,
  },
  comprehensive: {
    label: "Comprehensive Analysis",
    description: "Complete molecular evaluation",
    estimatedCost: 0.1,
  },
} as const

// Job Status Configuration
export const JOB_STATUS = {
  pending: {
    label: "Pending",
    color: "gray",
    icon: "clock",
  },
  running: {
    label: "Running",
    color: "blue",
    icon: "loader",
  },
  completed: {
    label: "Completed",
    color: "green",
    icon: "check-circle",
  },
  failed: {
    label: "Failed",
    color: "red",
    icon: "x-circle",
  },
} as const

// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

// File Upload Configuration
export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
export const ALLOWED_PROTEIN_FORMATS = [".pdb", ".pdbqt"]
export const ALLOWED_LIGAND_FORMATS = [".sdf", ".mol2", ".pdbqt"]

// Pagination
export const JOBS_PER_PAGE = 10
export const REPORTS_PER_PAGE = 20

// Cache Duration (in seconds)
export const CACHE_DURATION = {
  balance: 10,
  jobs: 5,
  reports: 30,
  transactions: 60,
} as const

// Feature Flags
export const FEATURES = {
  blockchain: true,
  aiAnalysis: true,
  reportGeneration: true,
  moleculeVisualization: true,
  stakeholderReports: true,
} as const

// Links
export const SOCIAL_LINKS = {
  twitter: "https://twitter.com/snowflake",
  github: "https://github.com/snowflake",
  discord: "https://discord.gg/snowflake",
  linkedin: "https://linkedin.com/company/snowflake",
} as const

export const FOOTER_LINKS = {
  product: [
    { label: "Features", href: "/#features" },
    { label: "Pricing", href: "/#pricing" },
    { label: "Dashboard", href: "/dashboard" },
    { label: "Blockchain", href: "/blockchain" },
  ],
  company: [
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
    { label: "Blog", href: "/blog" },
    { label: "Careers", href: "/careers" },
  ],
  resources: [
    { label: "Documentation", href: "/docs" },
    { label: "API Reference", href: "/api" },
    { label: "Tutorials", href: "/tutorials" },
    { label: "Support", href: "/support" },
  ],
  legal: [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
    { label: "Cookie Policy", href: "/cookies" },
    { label: "License", href: "/license" },
  ],
} as const
