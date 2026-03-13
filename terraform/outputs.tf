output "backend_url" {
  description = "Backend Cloud Run service URL"
  value       = module.cloud_run.backend_url
}

output "frontend_url" {
  description = "Frontend Cloud Run service URL"
  value       = module.cloud_run.frontend_url
}

output "load_balancer_ip" {
  description = "Global load balancer IP address"
  value       = module.cloud_run.load_balancer_ip
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = module.cloud_sql.connection_name
}
