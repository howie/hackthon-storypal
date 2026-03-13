variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in org/repo format (e.g. howie/hackthon-storypal)"
  type        = string
}

variable "project_number" {
  description = "GCP project number (used to build Workload Identity provider resource name)"
  type        = string
}
