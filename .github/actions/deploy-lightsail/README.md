# Deploy to AWS Lightsail - Composite Action

A reusable GitHub Action for deploying applications to AWS Lightsail with automatic dependency management.

## Features

- 🚀 Automated deployment to AWS Lightsail
- 📦 Automatic dependency installation (PHP, Python, Node.js, MySQL, etc.)
- 🧪 Optional testing before deployment
- ✅ Deployment verification
- 🔧 Configurable via YAML file

## Usage

### Basic Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Checkout deployment scripts
        uses: actions/checkout@v4
        with:
          repository: YOUR-USERNAME/YOUR-REPO
          path: .deployment-scripts
      
      - name: Copy deployment files
        run: |
          cp -r .deployment-scripts/workflows ./
          cp .deployment-scripts/deployment-generic.config.yml ./
      
      - name: Deploy to Lightsail
        uses: YOUR-USERNAME/YOUR-REPO/.github/actions/deploy-lightsail@main
        with:
          config-file: 'deployment-generic.config.yml'
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `config-file` | No | `deployment-generic.config.yml` | Path to deployment configuration file |
| `aws-access-key-id` | Yes | - | AWS Access Key ID |
| `aws-secret-access-key` | Yes | - | AWS Secret Access Key |
| `aws-region` | No | (from config) | AWS region (overrides config file) |
| `instance-name` | No | (from config) | Lightsail instance name (overrides config) |
| `skip-tests` | No | `false` | Skip running tests |
| `verify-deployment` | No | `true` | Verify deployment after completion |

## Outputs

| Output | Description |
|--------|-------------|
| `deployment-url` | URL of the deployed application |
| `deployment-status` | Status of the deployment (success/failed) |
| `static-ip` | Static IP address of the instance |

## Configuration File

Create a `deployment-generic.config.yml` file in your repository:

```yaml
aws:
  region: us-east-1

lightsail:
  instance_name: my-app-instance
  static_ip: 1.2.3.4

application:
  name: my-app
  type: web
  version: 1.0.0
  package_files:
    - index.php
    - config/
  package_fallback: true

dependencies:
  php:
    enabled: true
    version: "8.1"
  mysql:
    enabled: true
    version: "8.0"
  nodejs:
    enabled: false
  python:
    enabled: false

github_actions:
  triggers:
    push_branches:
      - main
  jobs:
    test:
      enabled: true
```

## Requirements

Your repository needs:
1. The `workflows/` directory from this repository
2. A `deployment-generic.config.yml` configuration file
3. AWS credentials stored as GitHub secrets

## Examples

### With Custom Config

```yaml
- name: Deploy to Lightsail
  uses: YOUR-USERNAME/YOUR-REPO/.github/actions/deploy-lightsail@main
  with:
    config-file: 'config/production.yml'
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Skip Tests

```yaml
- name: Deploy to Lightsail
  uses: YOUR-USERNAME/YOUR-REPO/.github/actions/deploy-lightsail@main
  with:
    config-file: 'deployment-generic.config.yml'
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    skip-tests: true
```

### Override Region and Instance

```yaml
- name: Deploy to Lightsail
  uses: YOUR-USERNAME/YOUR-REPO/.github/actions/deploy-lightsail@main
  with:
    config-file: 'deployment-generic.config.yml'
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: 'us-west-2'
    instance-name: 'my-custom-instance'
```

### Use Outputs

```yaml
- name: Deploy to Lightsail
  id: deploy
  uses: YOUR-USERNAME/YOUR-REPO/.github/actions/deploy-lightsail@main
  with:
    config-file: 'deployment-generic.config.yml'
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

- name: Show deployment info
  run: |
    echo "Deployed to: ${{ steps.deploy.outputs.deployment-url }}"
    echo "Status: ${{ steps.deploy.outputs.deployment-status }}"
    echo "IP: ${{ steps.deploy.outputs.static-ip }}"
```

## License

[Your License Here]
