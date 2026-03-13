variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "domain" {
  type = string
}

variable "backend_image" {
  type = string
}

variable "frontend_image" {
  type = string
}

variable "cloud_sql_connection_name" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_user" {
  type = string
}

variable "secret_ids" {
  description = "Map of secret name to secret ID"
  type        = map(string)
}

# ── Backend Cloud Run Service ────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  project  = var.project_id
  name     = "storypal-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.cloud_sql_connection_name]
      }
    }

    containers {
      image = var.backend_image

      ports {
        container_port = 8888
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "APP_ENV"
        value = "production"
      }

      env {
        name  = "DEBUG"
        value = "false"
      }

      env {
        name  = "DATABASE_HOST"
        value = "/cloudsql/${var.cloud_sql_connection_name}"
      }

      env {
        name  = "DATABASE_NAME"
        value = var.db_name
      }

      env {
        name  = "DATABASE_USER"
        value = var.db_user
      }

      env {
        name  = "CORS_ORIGINS"
        value = "https://${var.domain}"
      }

      env {
        name  = "STORAGE_TYPE"
        value = "gcs"
      }

      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.secret_ids["DATABASE_PASSWORD"]
            version = "latest"
          }
        }
      }

      env {
        name = "JWT_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_ids["JWT_SECRET_KEY"]
            version = "latest"
          }
        }
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_ids["GEMINI_API_KEY"]
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_OAUTH_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = var.secret_ids["GOOGLE_OAUTH_CLIENT_ID"]
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.secret_ids["GOOGLE_OAUTH_CLIENT_SECRET"]
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
  }
}

# ── Frontend Cloud Run Service ───────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  project  = var.project_id
  name     = "storypal-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.frontend_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      env {
        name  = "VITE_API_BASE_URL"
        value = "https://${var.domain}"
      }
    }
  }
}

# ── IAM — allow unauthenticated access via LB ───────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  name     = google_cloud_run_v2_service.frontend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Serverless NEGs ──────────────────────────────────────────────────────────

resource "google_compute_region_network_endpoint_group" "backend_neg" {
  project               = var.project_id
  name                  = "storypal-backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.backend.name
  }
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  project               = var.project_id
  name                  = "storypal-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.frontend.name
  }
}

# ── Backend Services ─────────────────────────────────────────────────────────

resource "google_compute_backend_service" "backend" {
  project     = var.project_id
  name        = "storypal-backend-bs"
  protocol    = "HTTP"
  timeout_sec = 300

  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }
}

resource "google_compute_backend_service" "frontend" {
  project     = var.project_id
  name        = "storypal-frontend-bs"
  protocol    = "HTTP"
  timeout_sec = 30

  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }
}

# ── URL Map (path-based routing) ─────────────────────────────────────────────

resource "google_compute_url_map" "default" {
  project         = var.project_id
  name            = "storypal-url-map"
  default_service = google_compute_backend_service.frontend.id

  host_rule {
    hosts        = [var.domain]
    path_matcher = "storypal"
  }

  path_matcher {
    name            = "storypal"
    default_service = google_compute_backend_service.frontend.id

    path_rule {
      paths   = ["/api/*", "/files/*", "/ws/*"]
      service = google_compute_backend_service.backend.id
    }
  }
}

# ── SSL Certificate ──────────────────────────────────────────────────────────

resource "google_compute_managed_ssl_certificate" "default" {
  project = var.project_id
  name    = "storypal-ssl-cert"

  managed {
    domains = [var.domain]
  }
}

# ── HTTPS Proxy & Forwarding Rule ────────────────────────────────────────────

resource "google_compute_target_https_proxy" "default" {
  project          = var.project_id
  name             = "storypal-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

resource "google_compute_global_address" "default" {
  project = var.project_id
  name    = "storypal-lb-ip"
}

resource "google_compute_global_forwarding_rule" "https" {
  project    = var.project_id
  name       = "storypal-https-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}

# ── HTTP → HTTPS redirect ───────────────────────────────────────────────────

resource "google_compute_url_map" "http_redirect" {
  project = var.project_id
  name    = "storypal-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  project = var.project_id
  name    = "storypal-http-redirect-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http_redirect" {
  project    = var.project_id
  name       = "storypal-http-redirect-rule"
  target     = google_compute_target_http_proxy.http_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.default.address
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "load_balancer_ip" {
  value = google_compute_global_address.default.address
}
