output "workload_identity_provider" {
  description = "Full Workload Identity Provider resource name (set as GCP_WORKLOAD_IDENTITY_PROVIDER GitHub Secret)"
  value       = "projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}"
}

output "service_account_email" {
  description = "GitHub Actions Service Account email (set as GCP_SERVICE_ACCOUNT GitHub Secret)"
  value       = google_service_account.github_actions.email
}
