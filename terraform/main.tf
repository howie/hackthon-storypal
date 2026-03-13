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

# ── Required APIs ─────────────────────────────────────────────────────────────

locals {
  required_apis = [
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "orgpolicy.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)
  project  = var.project_id
  service  = each.value

  disable_on_destroy         = false
  disable_dependent_services = false
}

# ── Cloud SQL VPC Peering (required for private IP) ───────────────────────────

resource "google_compute_global_address" "private_ip_range" {
  project       = var.project_id
  name          = "private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = "projects/${var.project_id}/global/networks/default"

  depends_on = [google_project_service.apis]
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = "projects/${var.project_id}/global/networks/default"
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]

  depends_on = [google_project_service.apis]
}

# ── Org Policy: allow allUsers IAM (hackathon public services) ────────────────

resource "google_org_policy_policy" "allow_all_iam_members" {
  name   = "projects/${var.project_id}/policies/iam.allowedPolicyMemberDomains"
  parent = "projects/${var.project_id}"

  spec {
    rules {
      allow_all = "TRUE"
    }
  }

  depends_on = [google_project_service.apis]
}

# ── Modules ──────────────────────────────────────────────────────────────────

module "artifact_registry" {
  source     = "./modules/artifact-registry"
  project_id = var.project_id
  region     = var.region

  depends_on = [google_project_service.apis]
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

  depends_on = [google_project_service.apis]
}

module "cloud_sql" {
  source     = "./modules/cloud-sql"
  project_id = var.project_id
  region     = var.region
  db_name    = var.db_name
  db_user    = var.db_user

  depends_on = [google_service_networking_connection.private_vpc]
}

module "workload_identity" {
  source         = "./modules/workload-identity"
  project_id     = var.project_id
  project_number = var.project_number
  github_repo    = var.github_repo

  depends_on = [google_project_service.apis]
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

  depends_on = [google_project_service.apis, google_org_policy_policy.allow_all_iam_members]
}
