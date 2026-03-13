variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

resource "google_artifact_registry_repository" "storypal" {
  project       = var.project_id
  location      = var.region
  repository_id = "storypal"
  description   = "StoryPal container images"
  format        = "DOCKER"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-latest-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
}

output "repository_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.storypal.repository_id}"
}
