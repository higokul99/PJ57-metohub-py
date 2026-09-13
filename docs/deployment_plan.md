# Deployment Plan for Glov-Py on Hostinger VPS

This document outlines the proposed deployment strategy for the `glov-py` FastAPI application to a Hostinger VPS (8GB RAM, 100GB Storage) using Docker, accommodating both Production and Test environments.

## Open Questions

1. **Domain Names:** Do you plan to use subdomains to separate traffic? (e.g., `api.glov.com` for production and `test.api.glov.com` for testing). If so, we should add an Nginx reverse proxy to route traffic based on the subdomain.
2. **GitHub Actions:** When you mentioned "github, docker for SCM", do you want me to write GitHub Actions workflows to automatically build and deploy code to the VPS when you push to the `main` or `test` branches?
3. **Database Setup:** The plan includes starting a MariaDB/MySQL container for the app. Do you want separate databases inside a single DB container, or entirely separate DB containers for Prod and Test to ensure complete isolation?

## Proposed Changes

### Docker Configuration
- **`Dockerfile`**: For building the FastAPI image (Python 3.11/3.12, installing requirements, and running Uvicorn on `0.0.0.0:8000`).
- **`.dockerignore`**: To ignore `.venv`, `__pycache__`, local `.env` files, and local `uploads/` directories.

### Environment Setup
- **`docker-compose.prod.yml`**: Will orchestrate the production FastAPI container and the production MariaDB container.
- **`docker-compose.test.yml`**: Will orchestrate the test FastAPI container and the test MariaDB container on separate ports.
- *(Optional)* **`docker-compose.nginx.yml`**: A central reverse proxy to route traffic if subdomains are used.

### Deployment Scripts (Optional)
- **`deploy.sh`**: A simple bash script to pull the latest code from GitHub and restart the Docker containers.

## Verification Plan

### Local Verification
- Build the Docker image locally to ensure it compiles without errors.
- Run `docker-compose` locally to verify that the FastAPI app connects to the MariaDB container successfully and that the `schema.sql` is properly initialized.

### Manual Verification (VPS)
- Clone the repository on the VPS, set up the `.env` variables, and run `docker-compose up -d`.
- Verify the app endpoints via the VPS IP address or domains.
