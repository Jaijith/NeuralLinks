# 2N1 Infrastructure as Code

This directory contains AWS CDK code for deploying the 2N1 application infrastructure.

## Stacks

- **DomainStack**: Route 53 hosted zone and ACM certificates
- **BackendStack**: Lambda function, API Gateway, S3 bucket for uploads
- **FrontendStack**: S3 bucket for frontend, CloudFront distribution

## Prerequisites

- AWS CLI configured
- Node.js 18+
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Setup

```bash
npm install
npm run build
```

## Deployment

```bash
# Deploy all stacks
npm run deploy

# Deploy individual stacks
npm run deploy:frontend
npm run deploy:backend
npm run deploy:domain

# View differences
npm run diff

# Destroy all stacks
npm run destroy
```

## Configuration

Edit `bin/app.ts` to change:
- Domain name
- AWS region
- Other configuration

