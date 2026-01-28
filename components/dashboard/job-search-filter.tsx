"use client"

import { useState, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { JobStatus } from "@/lib/api-client"

interface JobSearchFilterProps {
  jobs: JobStatus[]
  onFilteredJobsChange?: (filtered: JobStatus[]) => void
  className?: string
}

export function JobSearchFilter({ jobs, onFilteredJobsChange, className }: JobSearchFilterProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  const filteredJobs = useMemo(() => {
    let filtered = [...jobs]

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (job) =>
          job.job_id.toLowerCase().includes(query) ||
          job.created_at.toLowerCase().includes(query) ||
          (job.protein_sequence && job.protein_sequence.toLowerCase().includes(query))
      )
    }

    // Filter by status
    if (statusFilter !== "all") {
      filtered = filtered.filter((job) => job.status === statusFilter)
    }

    // Notify parent component
    onFilteredJobsChange?.(filtered)

    return filtered
  }, [jobs, searchQuery, statusFilter, onFilteredJobsChange])

  return (
    <div className={`flex flex-col sm:flex-row gap-3 ${className}`}>
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search jobs by ID, date, or sequence..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 pr-9"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
            onClick={() => setSearchQuery("")}
            aria-label="Clear search"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
      <Select value={statusFilter} onValueChange={setStatusFilter}>
        <SelectTrigger className="w-full sm:w-[180px]">
          <SelectValue placeholder="Filter by status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Status</SelectItem>
          <SelectItem value="queued">Queued</SelectItem>
          <SelectItem value="predicting_structure">Predicting Structure</SelectItem>
          <SelectItem value="structure_predicted">Structure Predicted</SelectItem>
          <SelectItem value="docking">Docking</SelectItem>
          <SelectItem value="running">Running</SelectItem>
          <SelectItem value="analyzing">Analyzing</SelectItem>
          <SelectItem value="completed">Completed</SelectItem>
          <SelectItem value="failed">Failed</SelectItem>
        </SelectContent>
      </Select>
      {(searchQuery || statusFilter !== "all") && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            Showing {filteredJobs.length} of {jobs.length} jobs
          </span>
        </div>
      )}
    </div>
  )
}
