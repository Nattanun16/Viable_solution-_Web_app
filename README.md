# Viable_solution Web App — Deployment Guide

This README covers quick steps to prepare and publish the Django app using Docker. It includes instructions for Render, Fly.io, and Google Cloud Run, plus optional S3 media setup.

Prerequisites
- Git repository (push your code to GitHub)
- Docker & Docker Compose (for local testing)
- A cloud provider account (Render / Fly / GCP)

1) Prepare repository

- Create a copy of environment variables:
```
cp .env.example .env
# Edit .env and fill secrets (DJANGO_SECRET_KEY, DATABASE_URL or POSTGRES_*, AWS_*, etc.)
```
- Install Python dependencies locally if needed:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

2) Local smoke test with Docker Compose

```
docker compose up --build -d
docker compose logs -f web
docker compose run --rm web python viable_graph_project/manage.py migrate
docker compose run --rm web python viable_graph_project/manage.py createsuperuser
```

Visit http://localhost:8000

3) Using AWS S3 for MEDIA (optional)
- Create an S3 bucket and an IAM user with `PutObject`/`GetObject` permissions.
- Put the credentials and bucket name in your environment (see `.env.example` variables starting with `AWS_`).
- The app already includes a settings switch: if `AWS_STORAGE_BUCKET_NAME` is set, uploads will use S3 via `django-storages`.

4) Deploy options

a) Render (Docker)
- Connect your GitHub repo in Render. Create a new Web Service → select Docker.
- Set Environment: `Docker` and point to branch `main`.
- Add Environment Variables on the Render dashboard: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL` (or individual POSTGRES_*), `RECAPTCHA_*`, `GOOGLE_VISION_API_KEY`, and any `AWS_*` if using S3.
- Create a managed Postgres on Render and copy the `DATABASE_URL` into the Web Service env.
- Deploy — then run migrations via Render shell or include a migration step in a deploy hook.

b) Fly.io (Docker)
- `fly launch` from your project directory and follow prompts.
- `fly postgres create` to provision a Postgres instance and set secrets.
- Set secrets:
```
fly secrets set DJANGO_SECRET_KEY=... DATABASE_URL=...
```
- `fly deploy`

**CI / Deploy automation (GitHub Actions)**

I included a sample GitHub Actions workflow at `.github/workflows/ci-deploy.yml` that:

- Builds the Docker image and pushes it to GitHub Container Registry (GHCR).
- Optionally pushes the image to DockerHub if you provide `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets.
- Optionally deploys to Fly.io when `FLY_API_TOKEN` and `FLY_APP_NAME` secrets are set.
- Optionally deploys to Google Cloud Run when `GCP_SA_KEY`, `GCP_PROJECT`, `GCP_REGION`, and `CLOUD_RUN_SERVICE` secrets are set.

Required repository secrets for the workflow (set in GitHub Settings → Secrets):

- `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (optional)
- `FLY_API_TOKEN` and `FLY_APP_NAME` (optional)
- `GCP_SA_KEY` (the JSON service account key, optional)
- `GCP_PROJECT`, `GCP_REGION`, `CLOUD_RUN_SERVICE` (for Cloud Run deploy)

The workflow tags images as `ghcr.io/<owner>/<repo>:<sha>` and uses that image for deploys when possible.

**Render**

I included a `render.yaml` manifest that can be used with Render (connect your repo and import the manifest). After importing, set the environment variables on the Render dashboard (do not store secrets in the repo):

- `DJANGO_SECRET_KEY` (set to a secure value)
- `DATABASE_URL` or the `POSTGRES_*` variables
- `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET_KEY`, `GOOGLE_VISION_API_KEY` (optional)
- If using S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME` (optional)

**AWS S3 Setup**

An example IAM policy for a dedicated user is at `aws/iam_policy_s3_media.json` — replace `your-bucket-name` with your bucket and attach this policy to an IAM user. Then set `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` as secrets on your host or provider.

Example AWS CLI commands to create a user and attach the policy (replace placeholders):

```bash
aws iam create-user --user-name viable-media-uploader
aws iam put-user-policy --user-name viable-media-uploader --policy-name S3MediaPolicy --policy-document file://aws/iam_policy_s3_media.json
aws iam create-access-key --user-name viable-media-uploader
```

The app will automatically use S3 for `MEDIA` uploads when `AWS_STORAGE_BUCKET_NAME` is set in the environment (see `viable_graph_project/settings.py`).


c) Google Cloud Run
- Build and push your Docker image to Container Registry / Artifact Registry.
- Create a Cloud SQL Postgres instance, configure connectivity (Cloud SQL Auth proxy or private IP).
- Set `DATABASE_URL` environment variable in Cloud Run, set other env vars, and deploy.

5) Post-deploy
- Always run migrations after deploy.
- Configure domain and enable HTTPS via the provider's dashboard.
- Set up periodic backups for Postgres and monitor logs.

If you want, I can (pick one):
- provide a `render.yaml` for Render, or
- generate a GitHub Actions workflow that builds and pushes your Docker image and deploys to Fly/GCP.

---

## Local image scanning (Docker / Trivy)

To check the built Docker image for vulnerabilities locally, use either Docker's scan (Snyk) or Trivy.

- Docker Scan (requires Docker Desktop with scanning enabled):

```bash
# After building the image locally
docker build -t viable-solution-web-app:local .
docker scan viable-solution-web-app:local
```

- Trivy (recommended, supports local image scanning):

```bash
# Option A: run Trivy container (no install)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.44.0 image --severity HIGH,CRITICAL --format table viable-solution-web-app:local

# Option B: install trivy locally (example installs the binary)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin 0.44.0
trivy image --severity HIGH,CRITICAL --format table viable-solution-web-app:local
```

Notes:
- The CI workflow will upload a `trivy-report` artifact when it runs on push. If the report shows HIGH/CRITICAL issues, update your base image or patch the vulnerable packages.
- If you'd like, I can add an automated fix step (pin base image, add multi-stage, or run `apt-get` upgrades) and make the CI fail on HIGH vulnerabilities.
