# PR Preview System

Automatic preview environments for every Pull Request using AWS Lightsail and GitHub Actions.

## Features

- 🚀 **Automatic Deployment**: Every PR gets its own preview environment
- 🔗 **Unique URLs**: Each PR has a dedicated URL for testing
- 🔄 **Auto Updates**: New commits automatically update the preview
- 🧹 **Auto Cleanup**: Resources are deleted when PR closes
- 💰 **Cost Efficient**: ~$0.005/hour per preview (nano instance)

## How It Works

1. Open a Pull Request
2. GitHub Actions triggers automatically
3. Creates AWS Lightsail instance
4. Deploys your application
5. Posts preview URL as PR comment
6. Updates on new commits
7. Deletes instance when PR closes

## Setup

### 1. Configure AWS Credentials

Add these secrets to your GitHub repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### 2. That's It!

The workflow will automatically run on PR events.

## Cost Estimate

- Nano instance: $3.50/month (~$0.005/hour)
- Average PR lifetime: 2-3 days
- Cost per PR: ~$0.25-$0.40

## Supported Applications

- React/Vue/Angular (static builds)
- Node.js APIs
- Python Flask/FastAPI
- Any application that can run on Ubuntu

## Repository

https://github.com/naveenraj44125-creator/pr-preview-system
