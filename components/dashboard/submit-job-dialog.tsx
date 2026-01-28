"use client"

import type React from "react"

import { useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Upload, Loader2, Dna, CheckCircle2, Info } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useToast } from "@/hooks/use-toast"
import type { DockingParameters } from "@/lib/api-client"

interface SubmitJobDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (
    jobType: "docking_only" | "sequence_to_docking",
    proteinFile: File | null,
    proteinSequence: string | null,
    ligandFile: File,
    parameters: DockingParameters,
  ) => Promise<void>
}

export function SubmitJobDialog({ open, onOpenChange, onSubmit }: SubmitJobDialogProps) {
  const { toast } = useToast()
  const [jobType, setJobType] = useState<"docking_only" | "sequence_to_docking">("docking_only")
  const [proteinFile, setProteinFile] = useState<File | null>(null)
  const [proteinSequence, setProteinSequence] = useState<string>("")
  const [ligandFile, setLigandFile] = useState<File | null>(null)
  const [exhaustiveness, setExhaustiveness] = useState([8])
  const [numModes, setNumModes] = useState([9])
  const [useGpu, setUseGpu] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{
    protein?: string
    sequence?: string
    ligand?: string
  }>({})

  const validateFile = (file: File, type: "protein" | "ligand"): boolean => {
    const maxSize = 50 * 1024 * 1024 // 50MB
    if (file.size > maxSize) {
      const error = `${type === "protein" ? "Protein" : "Ligand"} file is too large (max 50MB)`
      setValidationError(error)
      setFieldErrors((prev) => ({ ...prev, [type]: error }))
      return false
    }

    if (type === "protein" && !file.name.endsWith(".pdb")) {
      const error = "Protein file must be in PDB format (.pdb)"
      setValidationError(error)
      setFieldErrors((prev) => ({ ...prev, protein: error }))
      return false
    }

    if (type === "ligand" && !file.name.match(/\.(sdf|mol2)$/i)) {
      const error = "Ligand file must be in SDF or MOL2 format"
      setValidationError(error)
      setFieldErrors((prev) => ({ ...prev, ligand: error }))
      return false
    }

    // Clear error for this field if validation passes
    setFieldErrors((prev) => ({ ...prev, [type]: undefined }))
    return true
  }

  const validateSequence = (sequence: string): boolean => {
    const cleanSeq = sequence.replace(/\s/g, "").replace(/^>.*\n/g, "")
    const validAminoAcids = /^[ACDEFGHIKLMNPQRSTVWY]+$/i

    if (cleanSeq.length < 20) {
      const error = "Sequence must be at least 20 amino acids long"
      setValidationError(error)
      setFieldErrors((prev) => ({ ...prev, sequence: error }))
      return false
    }

    if (!validAminoAcids.test(cleanSeq)) {
      const error = "Sequence contains invalid amino acid codes. Use standard one-letter codes (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y)"
      setValidationError(error)
      setFieldErrors((prev) => ({ ...prev, sequence: error }))
      return false
    }

    // Clear error if validation passes
    setFieldErrors((prev) => ({ ...prev, sequence: undefined }))
    return true
  }

  const handleProteinFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    if (file && validateFile(file, "protein")) {
      setProteinFile(file)
      setValidationError(null)
    }
  }

  const handleLigandFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    if (file && validateFile(file, "ligand")) {
      setLigandFile(file)
      setValidationError(null)
    }
  }

  const handleSequenceChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setProteinSequence(value)
    if (value) {
      validateSequence(value)
    } else {
      setFieldErrors((prev) => ({ ...prev, sequence: undefined }))
    }
  }

  const handleSubmit = async () => {
    setValidationError(null)

    if (jobType === "docking_only") {
      if (!proteinFile) {
        setValidationError("Please select a protein PDB file")
        return
      }
    } else {
      if (!proteinSequence) {
        setValidationError("Please enter a protein sequence")
        return
      }
      if (!validateSequence(proteinSequence)) {
        return
      }
    }

    if (!ligandFile) {
      setValidationError("Please select a ligand file")
      return
    }

    const parameters: DockingParameters = {
      grid_center_x: 0,
      grid_center_y: 0,
      grid_center_z: 0,
      grid_size_x: 20,
      grid_size_y: 20,
      grid_size_z: 20,
      exhaustiveness: exhaustiveness[0],
      energy_range: 3,
      num_modes: numModes[0],
      use_gpu: useGpu,
    }

    setIsSubmitting(true)
    try {
      await onSubmit(jobType, proteinFile, proteinSequence || null, ligandFile, parameters)
      
      // Success toast
      toast({
        title: "Job submitted successfully",
        description: jobType === "sequence_to_docking" 
          ? "AlphaFold structure prediction started. This may take 5-30 minutes."
          : "Docking job queued. Results will appear shortly.",
      })
      
      // Reset form
      setProteinFile(null)
      setProteinSequence("")
      setLigandFile(null)
      setExhaustiveness([8])
      setNumModes([9])
      setUseGpu(false)
      setValidationError(null)
      setFieldErrors({})
      setJobType("docking_only")
      onOpenChange(false)
    } catch (error) {
      console.error("[v0] Submit error:", error)
      const errorMessage = error instanceof Error ? error.message : "Failed to submit job"
      setValidationError(errorMessage)
      toast({
        title: "Submission failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Submit Docking Job</DialogTitle>
          <DialogDescription>
            Choose to upload a PDB file or predict structure from sequence, then configure docking parameters.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {validationError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{validationError}</AlertDescription>
            </Alert>
          )}

          <Tabs value={jobType} onValueChange={(v) => setJobType(v as typeof jobType)}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="docking_only" className="gap-2">
                <Upload className="w-4 h-4" />
                Use PDB File
              </TabsTrigger>
              <TabsTrigger value="sequence_to_docking" className="gap-2">
                <Dna className="w-4 h-4" />
                Predict from Sequence
              </TabsTrigger>
            </TabsList>

            <TabsContent value="docking_only" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="protein">Protein File (PDB)</Label>
                <div className="flex items-center gap-2">
                  <Input 
                    id="protein" 
                    type="file" 
                    accept=".pdb" 
                    onChange={handleProteinFileChange}
                    aria-invalid={!!fieldErrors.protein}
                    aria-describedby={fieldErrors.protein ? "protein-error" : undefined}
                  />
                  {proteinFile && (
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      <span className="text-muted-foreground">{proteinFile.name}</span>
                      <span className="text-xs text-muted-foreground">
                        ({(proteinFile.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                  )}
                </div>
                {fieldErrors.protein ? (
                  <p className="text-xs text-destructive" id="protein-error" role="alert">
                    {fieldErrors.protein}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">Upload your protein structure in PDB format (max 50MB)</p>
                )}
              </div>
            </TabsContent>

            <TabsContent value="sequence_to_docking" className="space-y-4 mt-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="sequence">Protein Sequence (FASTA)</Label>
                  {proteinSequence && (
                    <span className="text-xs text-muted-foreground">
                      {proteinSequence.replace(/\s/g, "").replace(/^>.*\n/g, "").length} amino acids
                    </span>
                  )}
                </div>
                <Textarea
                  id="sequence"
                  placeholder={">my_protein\nMKVLWALLLVWPWVAFAVE..."}
                  value={proteinSequence}
                  onChange={handleSequenceChange}
                  className={`font-mono text-sm h-32 ${fieldErrors.sequence ? "border-destructive" : ""}`}
                  aria-invalid={!!fieldErrors.sequence}
                  aria-describedby={fieldErrors.sequence ? "sequence-error" : "sequence-help"}
                />
                {fieldErrors.sequence ? (
                  <p className="text-xs text-destructive" id="sequence-error" role="alert">
                    {fieldErrors.sequence}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground" id="sequence-help">
                    Enter amino acid sequence in FASTA format. AlphaFold will predict the 3D structure. Minimum 20 amino acids required.
                  </p>
                )}
              </div>
              <Alert>
                <Dna className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  Structure prediction may take 5-30 minutes depending on sequence length and queue.
                </AlertDescription>
              </Alert>
            </TabsContent>
          </Tabs>

          {/* Ligand File Upload */}
          <div className="space-y-2">
            <Label htmlFor="ligand">Ligand File (SDF/MOL2)</Label>
            <div className="flex items-center gap-2">
              <Input 
                id="ligand" 
                type="file" 
                accept=".sdf,.mol2" 
                onChange={handleLigandFileChange}
                aria-invalid={!!fieldErrors.ligand}
                aria-describedby={fieldErrors.ligand ? "ligand-error" : undefined}
              />
              {ligandFile && (
                <div className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <span className="text-muted-foreground">{ligandFile.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({(ligandFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              )}
            </div>
            {fieldErrors.ligand ? (
              <p className="text-xs text-destructive" id="ligand-error" role="alert">
                {fieldErrors.ligand}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">Upload ligand structure in SDF or MOL2 format (max 50MB)</p>
            )}
          </div>

          {/* Docking Parameters */}
          <div className="space-y-4 pt-4 border-t">
            <h4 className="font-medium">Docking Parameters</h4>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Label htmlFor="exhaustiveness">Exhaustiveness</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className="inline-flex">
                        <Info className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground transition-colors" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>
                        Controls how thoroughly AutoDock Vina searches for binding poses. Higher values (8-20) provide more accurate results but take longer. Recommended: 8 for quick screening, 16+ for publication-quality results.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <span className="text-sm text-muted-foreground">{exhaustiveness[0]}</span>
              </div>
              <Slider
                id="exhaustiveness"
                min={1}
                max={20}
                step={1}
                value={exhaustiveness}
                onValueChange={setExhaustiveness}
                aria-label="Exhaustiveness level"
              />
              <p className="text-xs text-muted-foreground">
                Higher values provide more thorough search but take longer
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Label htmlFor="modes">Number of Modes</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className="inline-flex">
                        <Info className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground transition-colors" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>
                        Number of distinct binding poses to generate and rank. More modes provide better coverage of binding possibilities. Typically 9 modes is sufficient for most analyses.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <span className="text-sm text-muted-foreground">{numModes[0]}</span>
              </div>
              <Slider 
                id="modes" 
                min={1} 
                max={20} 
                step={1} 
                value={numModes} 
                onValueChange={setNumModes}
                aria-label="Number of binding modes"
              />
              <p className="text-xs text-muted-foreground">Number of binding modes to generate</p>
            </div>

            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-2 space-y-0.5">
                <Label htmlFor="use-gpu">GPU-accelerated docking (Gnina)</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className="inline-flex">
                      <Info className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground transition-colors" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p>
                      Use Gnina for GPU-accelerated docking when available. Requires Gnina installed and USE_GPU_DOCKING enabled on the server. Falls back to AutoDock Vina if GPU is not available.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <Switch
                id="use-gpu"
                checked={useGpu}
                onCheckedChange={setUseGpu}
                aria-label="Use GPU-accelerated docking"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || (!proteinFile && !proteinSequence) || !ligandFile}
            className="gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Submit Job
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
