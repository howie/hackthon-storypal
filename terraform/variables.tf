variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-east1"
}

variable "domain" {
  description = "Custom domain for the application"
  type        = string
  default     = "demo.heyuai.com.tw"
}

variable "db_name" {
  description = "Cloud SQL database name"
  type        = string
  default     = "storypal"
}

variable "db_user" {
  description = "Cloud SQL database user"
  type        = string
  default     = "storypal"
}

variable "backend_image" {
  description = "Backend container image URL"
  type        = string
}

variable "frontend_image" {
  description = "Frontend container image URL"
  type        = string
}
