variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_user" {
  type = string
}

resource "google_sql_database_instance" "main" {
  project          = var.project_id
  name             = "storypal-postgres"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = false
      private_network = "projects/${var.project_id}/global/networks/default"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "storypal" {
  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "storypal" {
  project  = var.project_id
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = "CHANGE_ME_VIA_CONSOLE"

  lifecycle {
    ignore_changes = [password]
  }
}

output "connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "instance_name" {
  value = google_sql_database_instance.main.name
}

output "private_ip" {
  value = google_sql_database_instance.main.private_ip_address
}
