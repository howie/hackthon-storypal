variable "project_id" {
  type = string
}

variable "secret_ids" {
  description = "List of secret names to create in Secret Manager"
  type        = list(string)
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(var.secret_ids)
  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }
}

output "secret_ids" {
  description = "Map of secret name to secret ID"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.secret_id }
}
