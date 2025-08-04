# Webhook Dispatcher

The Webhook Dispatcher is a microservice that receives GitHub webhooks and processes them for operator pipelines.
It validates webhooks, stores events in a database, and triggers Tekton pipelines for operator pipelines with
a capacity management system.

## Overview

The Webhook Dispatcher serves as the entry point for GitHub events in the operator pipelines.
When developers submit operators via pull requests, the dispatcher:

1. **Receives and validates** GitHub webhooks with signature verification
2. **Stores webhook events** in a PostgreSQL database
3. **Manages pipeline capacity** to prevent resource exhaustion
4. **Triggers Tekton pipelines** for operator validation

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Webhook        │    │   PostgreSQL    │
│   Webhooks      │───▶│   Dispatcher     │───▶│   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Tekton         │
                       │   Pipelines      │
                       └──────────────────┘
```

## Features

- **Secure webhook processing** with HMAC-SHA256 signature verification
- **Multi-repository support** with configurable processing rules
- **Pipeline capacity management** to prevent resource overload
- **Background event processing** for improved performance
- **Health monitoring** and status tracking


## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Kubernetes/OpenShift cluster access

### Setup

1. Install dependencies:
```bash
pdm install --no-dev
```

2. Create database:
```bash
docker compose up -d
```

3. Set environment variables:
```bash
export DATABASE_URL="postgresql://webhook_user:secure_password@localhost:5432/webhook_dispatcher"
export GITHUB_WEBHOOK_SECRET="your_github_webhook_secret"
```

## Configuration

Create a `dispatcher_config.yaml` file:

```yaml
---
dispatcher:
  items:
    - name: "Community Operators"
      events:
        - opened
        - synchronize
        - ready_for_review
      full_repository_name: "redhat-openshift-ecosystem/community-operators"
      capacity:
        type: ocp_tekton
        pipeline_name: "operator-hosted-pipeline"
        max_capacity: 5
        namespace: "operator-pipeline-prod"
      # Tekton pipeline listener URL
      callback_url: "https://tekton-dashboard.example.com/api/v1/trigger"

security:
  github_webhook_secret: "${GITHUB_WEBHOOK_SECRET}"
  verify_signatures: true
  allowed_github_events:
    - pull_request
```

### Configuration Parameters

- **name**: Configuration identifier
- **events**: GitHub PR events to process
- **full_repository_name**: Repository in `owner/repo` format
- **capacity**: Pipeline capacity settings
- **callback_url**: Tekton pipeline trigger URL
- **github_webhook_secret**: Webhook signature verification secret

## Usage

### Running the Service

Production mode:
```bash
export WEBHOOK_DISPATCHER_CONFIG="/path/to/dispatcher_config.yaml"
python -m operatorcert.webhook_dispatcher.main
```

### GitHub Webhook Setup

1. Go to repository **Settings** → **Webhooks**
2. Add webhook with:
   - **URL**: `https://your-domain.com/api/v1/webhooks/github-pipeline`
   - **Content type**: `application/json`
   - **Secret**: Your webhook secret
   - **Events**: Pull requests

## API Endpoints

- `POST /api/v1/webhooks/github-pipeline` - Receive GitHub webhooks
- `GET /api/v1/status/ping` - Health check
- `GET /api/v1/status/db` - Database health
- `GET /api/v1/events/status` - Event status with pagination

## Security

- **HMAC-SHA256 signature verification** for all webhook requests
- **GitHub User-Agent validation** to prevent spoofing
- **Event type filtering** based on configuration
- **TLS encryption** required for production deployments

## Monitoring

### Health Checks
```bash
curl http://localhost:5000/api/v1/status/ping
curl http://localhost:5000/api/v1/status/db
```

### Event Status
```bash
curl "http://localhost:5000/api/v1/events/status?page_size=20"
```

## Troubleshooting

### Common Issues

**Signature verification failures**:
- Verify `GITHUB_WEBHOOK_SECRET` matches GitHub configuration
- Ensure webhook uses `application/json` content type

**Database connection errors**:
- Check `DATABASE_URL` format
- Verify PostgreSQL is running and accessible

**Event processing delays**:
- Check dispatcher thread logs
- Monitor pipeline capacity usage
- Review database performance

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
python -m operatorcert.webhook_dispatcher.main --verbose
```

For support, refer to the [operator-pipelines repository](https://github.com/redhat-openshift-ecosystem/operator-pipelines).
