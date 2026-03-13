terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "storypal-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Modules ──────────────────────────────────────────────────────────────────

module "artifact_registry" {
  source     = "./modules/artifact-registry"
  project_id = var.project_id
  region     = var.region
}

module "secrets" {
  source     = "./modules/secret-manager"
  project_id = var.project_id
  secret_ids = [
    "JWT_SECRET_KEY",
    "GEMINI_API_KEY",
    "DATABASE_PASSWORD",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
  ]
}

module "cloud_sql" {
  source     = "./modules/cloud-sql"
  project_id = var.project_id
  region     = var.region
  db_name    = var.db_name
  db_user    = var.db_user
}

module "cloud_run" {
  source     = "./modules/cloud-run"
  project_id = var.project_id
  region     = var.region
  domain     = var.domain

  backend_image  = var.backend_image
  frontend_image = var.frontend_image

  cloud_sql_connection_name = module.cloud_sql.connection_name
  db_name                   = var.db_name
  db_user                   = var.db_user

  secret_ids = module.secrets.secret_ids
}
