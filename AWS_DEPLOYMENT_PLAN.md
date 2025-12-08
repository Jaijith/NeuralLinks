# AWS Serverless Deployment Plan for 2N1
## Maximum Serverless Architecture with Cost Optimization

---

## 📋 Executive Summary

This plan outlines a **fully serverless AWS deployment** strategy that minimizes costs while maintaining scalability, performance, and reliability. The architecture leverages AWS Lambda, API Gateway, S3, CloudFront, and managed services to eliminate server management and reduce operational overhead.

**Estimated Monthly Cost (Low Traffic): $50-150/month**
**Estimated Monthly Cost (Medium Traffic): $200-500/month**
**Estimated Monthly Cost (High Traffic): $500-1500/month**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CloudFront CDN                            │
│                    (Static Assets + API Cache)                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼────────┐            ┌────────▼──────────┐
│   S3 Bucket    │            │   API Gateway    │
│  (Frontend)    │            │   (REST API)      │
└────────────────┘            └────────┬──────────┘
                                       │
                            ┌──────────┴──────────┐
                            │                      │
                    ┌───────▼──────┐      ┌───────▼──────┐
                    │   Lambda     │      │   Lambda      │
                    │  (FastAPI)   │      │  (Workers)    │
                    └───────┬──────┘      └───────┬──────┘
                            │                      │
                    ┌───────┴──────────────────────┴──────┐
                    │                                       │
            ┌───────▼────────┐                    ┌────────▼──────┐
            │   MongoDB      │                    │   S3 Bucket    │
            │   Atlas        │                    │  (File Store)  │
            └────────────────┘                    └────────────────┘
```

---

## 🎯 Component-by-Component Deployment Plan

### 1. **Frontend (React SPA)**

#### **Service: AWS S3 + CloudFront**

**Architecture:**
- **S3 Bucket**: Host static React build files
- **CloudFront Distribution**: CDN for global content delivery and caching
- **Route 53** (Optional): Custom domain management
- **ACM (AWS Certificate Manager)**: Free SSL/TLS certificates

**Configuration:**
```yaml
S3 Bucket:
  - Name: 2n1-frontend-prod
  - Static Website Hosting: Disabled (CloudFront handles this)
  - Versioning: Enabled (for rollbacks)
  - Lifecycle Rules: Archive old versions to Glacier after 90 days

CloudFront:
  - Origin: S3 bucket
  - Behaviors:
    - Default: Cache static assets (CSS, JS, images) for 1 year
    - API Proxy: Forward /api/* to API Gateway
  - Price Class: Use Only North America and Europe (cheaper)
  - Compression: Enabled
  - Custom Error Pages: Redirect 404 to index.html (SPA routing)
```

**Cost:**
- S3 Storage: ~$0.023/GB/month (minimal for static files)
- S3 Requests: ~$0.005 per 1,000 requests
- CloudFront: ~$0.085/GB (first 10TB) + $0.01 per 10,000 requests
- **Estimated: $5-20/month** (depending on traffic)

**Deployment Steps:**
1. Build React app: `npm run build`
2. Upload `build/` contents to S3 bucket
3. Create CloudFront distribution pointing to S3
4. Configure custom domain (optional)
5. Set up CI/CD with GitHub Actions or AWS CodePipeline

---

### 2. **Backend API (FastAPI)**

#### **Service: AWS Lambda + API Gateway**

**Architecture Options:**

#### **Option A: Lambda Function URL (Simpler, Cheaper)**
- Single Lambda function with FastAPI
- Direct HTTP endpoint (no API Gateway)
- **Best for: Simple deployments, lower cost**

#### **Option B: API Gateway + Lambda (More Features)**
- API Gateway REST API
- Lambda function with FastAPI
- **Best for: Advanced features (rate limiting, API keys, caching)**

**Recommendation: Start with Option A, migrate to Option B if needed**

#### **Option A: Lambda Function URL**

**Configuration:**
```yaml
Lambda Function:
  - Runtime: Python 3.11 or 3.12
  - Memory: 1024 MB (adjust based on performance)
  - Timeout: 30 seconds (max for API Gateway, 15 min for Function URL)
  - Architecture: x86_64 (cheaper than ARM)
  - Environment Variables:
    - MONGODB_URI
    - GOOGLE_CLIENT_ID
    - GOOGLE_CLIENT_SECRET
    - AWS_S3_BUCKET
    - CORS_ORIGINS
    - AZURE_OPENAI_API_KEY
    - etc.
  - Layers: (Optional) Common dependencies layer
  - VPC: Not needed (MongoDB Atlas is external)

Lambda Function URL:
  - Auth Type: AWS_IAM or NONE (with CORS)
  - CORS: Configure for frontend domain
  - Invoke Mode: RESPONSE_STREAM (if needed for streaming)
```

**Cost:**
- Lambda: $0.20 per 1M requests + $0.0000166667 per GB-second
- **Estimated: $10-100/month** (depending on requests and execution time)

**Deployment Steps:**
1. Package FastAPI app with dependencies
2. Create Lambda deployment package (or use container image)
3. Create Lambda function
4. Create Function URL
5. Update frontend API endpoint

#### **Option B: API Gateway + Lambda**

**Configuration:**
```yaml
API Gateway:
  - Type: REST API (HTTP API is cheaper but less features)
  - CORS: Enabled
  - Throttling: 10,000 requests/second (default)
  - Caching: Enable for GET requests (optional)
  - Custom Domain: api.2n1.com (optional)

Lambda:
  - Same as Option A
  - Integration: Lambda Proxy Integration
```

**Cost:**
- API Gateway: $3.50 per million requests (REST API)
- Lambda: Same as Option A
- **Estimated: $15-150/month**

---

### 3. **Database (MongoDB)**

#### **Service: MongoDB Atlas (Recommended) or AWS DocumentDB**

**Recommendation: MongoDB Atlas** (Better cost, easier management)

**MongoDB Atlas Configuration:**
```yaml
Cluster:
  - Tier: M0 (Free) → M10 ($57/month) → M30 ($200/month)
  - Region: Same as Lambda (us-east-1 recommended)
  - Backup: Enabled (automated)
  - Network Access: Whitelist Lambda IPs or 0.0.0.0/0 (with auth)
  - Database Users: Create app user with read/write permissions
```

**Cost:**
- M0 (Free): 512MB storage, shared CPU (development only)
- M10: $57/month - 2GB storage, shared CPU
- M30: $200/month - 10GB storage, dedicated CPU
- **Recommended: Start with M10, scale to M30 as needed**

**Alternative: AWS DocumentDB**
- More expensive but fully managed in AWS
- Better integration with AWS services
- **Cost: ~$200-500/month** (minimum cluster)

---

### 4. **File Storage (Images, Uploads)**

#### **Service: AWS S3**

**Configuration:**
```yaml
S3 Bucket:
  - Name: 2n1-uploads-prod
  - Versioning: Disabled (to save costs)
  - Lifecycle Rules:
    - Move to Glacier after 90 days (archived files)
    - Delete incomplete multipart uploads after 7 days
  - CORS: Configure for frontend domain
  - Public Access: Block all (use CloudFront or presigned URLs)
  - Encryption: AES-256 (server-side)

CloudFront Distribution (Optional):
  - Origin: S3 bucket
  - Cache Policy: Cache-Control max-age
  - Signed URLs: For private content
```

**Cost:**
- S3 Storage: $0.023/GB/month
- S3 PUT Requests: $0.005 per 1,000
- S3 GET Requests: $0.0004 per 1,000
- Data Transfer Out: $0.09/GB (first 10TB)
- **Estimated: $5-50/month** (depending on storage and traffic)

**Implementation:**
- Update `backend/utils/file_storage.py` to use boto3 for S3 uploads
- Use presigned URLs for secure file access
- Implement image optimization (Lambda@Edge or separate Lambda)

---

### 5. **Authentication (Google OAuth)**

#### **Service: Keep Google OAuth (No AWS Service Needed)**

**Configuration:**
- Continue using Google OAuth
- Store OAuth credentials in AWS Secrets Manager or Lambda environment variables
- Update redirect URIs to production domain

**Cost: Free** (Google OAuth is free)

**Alternative: AWS Cognito**
- More AWS-native but adds complexity
- **Cost: Free tier (50,000 MAU), then $0.0055 per MAU**

---

### 6. **Background Jobs / Workers**

#### **Service: AWS Lambda (Scheduled) or EventBridge + Lambda**

**Use Cases:**
- Avatar autonomous actions
- Scheduled tasks
- Background processing

**Configuration:**
```yaml
EventBridge Rules:
  - Schedule: Cron expressions (e.g., every 5 minutes)
  - Target: Lambda function

Lambda Functions:
  - Separate functions for different tasks
  - Timeout: 15 minutes (max)
  - Memory: 512 MB (adjust as needed)
```

**Cost:**
- EventBridge: $1.00 per million events
- Lambda: Same pricing as API Lambda
- **Estimated: $5-30/month**

---

### 7. **Monitoring & Logging**

#### **Services: CloudWatch (Free Tier) + X-Ray (Optional)**

**Configuration:**
```yaml
CloudWatch:
  - Logs: Automatic for Lambda
  - Metrics: Automatic for Lambda, API Gateway
  - Alarms: Set up for errors, high latency
  - Dashboards: Create custom dashboards

X-Ray (Optional):
  - Distributed tracing
  - Performance insights
  - Cost: $5 per million traces
```

**Cost:**
- CloudWatch Logs: Free tier (5GB ingestion, 5GB storage)
- CloudWatch Metrics: Free tier (10 custom metrics)
- **Estimated: $0-20/month** (mostly free tier)

---

### 8. **CI/CD Pipeline**

#### **Service: GitHub Actions (Free) or AWS CodePipeline**

**GitHub Actions (Recommended - Free for public repos):**
```yaml
Workflow:
  1. On push to main branch
  2. Build frontend (npm run build)
  3. Upload to S3
  4. Invalidate CloudFront cache
  5. Build backend Lambda package
  6. Deploy Lambda function
```

**Cost: Free** (GitHub Actions free tier: 2,000 minutes/month)

**AWS CodePipeline:**
- More AWS-native but costs money
- **Cost: $1 per active pipeline/month**

---

## 📊 Cost Breakdown (Monthly Estimates)

### **Low Traffic (1,000 users, 100K requests/month)**
| Service | Cost |
|---------|------|
| S3 (Frontend) | $1 |
| CloudFront | $5 |
| Lambda (API) | $10 |
| MongoDB Atlas M10 | $57 |
| S3 (Uploads) | $5 |
| CloudWatch | $0 (free tier) |
| **Total** | **~$78/month** |

### **Medium Traffic (10,000 users, 1M requests/month)**
| Service | Cost |
|---------|------|
| S3 (Frontend) | $5 |
| CloudFront | $30 |
| Lambda (API) | $50 |
| MongoDB Atlas M30 | $200 |
| S3 (Uploads) | $20 |
| CloudWatch | $10 |
| **Total** | **~$315/month** |

### **High Traffic (100,000 users, 10M requests/month)**
| Service | Cost |
|---------|------|
| S3 (Frontend) | $20 |
| CloudFront | $200 |
| Lambda (API) | $300 |
| MongoDB Atlas M50 | $500 |
| S3 (Uploads) | $100 |
| CloudWatch | $50 |
| **Total** | **~$1,170/month** |

---

## 🚀 Deployment Steps (Phase-by-Phase)

### **Phase 1: Infrastructure Setup (Week 1)**
1. Create AWS account and set up billing alerts
2. Create S3 buckets (frontend, uploads)
3. Set up MongoDB Atlas cluster
4. Create IAM roles and policies
5. Set up CloudWatch logging

### **Phase 2: Backend Deployment (Week 2)**
1. Package FastAPI app for Lambda
2. Create Lambda function
3. Configure environment variables
4. Set up Lambda Function URL or API Gateway
5. Test API endpoints
6. Update file storage to use S3

### **Phase 3: Frontend Deployment (Week 3)**
1. Build React app for production
2. Upload to S3
3. Create CloudFront distribution
4. Configure custom domain (optional)
5. Update API endpoints in frontend
6. Test end-to-end

### **Phase 4: CI/CD & Optimization (Week 4)**
1. Set up GitHub Actions workflow
2. Configure auto-deployment
3. Set up monitoring and alerts
4. Optimize Lambda cold starts
5. Enable CloudFront caching
6. Performance testing

---

## 🔧 Required Code Changes

### **1. Backend Changes**

#### **Lambda Handler Wrapper**
Create `backend/lambda_handler.py`:
```python
from mangum import Mangum
from app.main import app

# Wrap FastAPI app for Lambda
handler = Mangum(app, lifespan="off")
```

#### **Update File Storage**
Modify `backend/utils/file_storage.py`:
- Implement S3 upload using boto3
- Use presigned URLs for file access
- Remove local file storage code

#### **Environment Variables**
- Move all config to Lambda environment variables
- Use AWS Secrets Manager for sensitive data (optional)

#### **Database Connection**
- Ensure MongoDB connection works with Lambda (connection pooling)
- Handle cold starts gracefully

### **2. Frontend Changes**

#### **API Endpoint Configuration**
Update `frontend/src/config/config.js`:
```javascript
export const API_BASE_URL = process.env.REACT_APP_API_URL || 
  'https://your-lambda-url.lambda-url.us-east-1.on.aws';
```

#### **Build Configuration**
- Optimize bundle size
- Enable code splitting
- Configure environment variables for production

---

## 🛡️ Security Considerations

1. **IAM Roles**: Use least privilege principle
2. **Secrets Management**: Use AWS Secrets Manager for sensitive data
3. **CORS**: Configure properly for production domain
4. **HTTPS**: Enforce HTTPS everywhere (CloudFront + API Gateway)
5. **Rate Limiting**: Implement at API Gateway level
6. **Input Validation**: Already in FastAPI, ensure it's comprehensive
7. **Database**: Use MongoDB Atlas network security features
8. **S3**: Block public access, use presigned URLs

---

## 📈 Scaling Strategy

### **Automatic Scaling**
- **Lambda**: Automatically scales to handle traffic
- **API Gateway**: Handles up to 10,000 requests/second
- **CloudFront**: Global CDN, handles massive traffic
- **S3**: Virtually unlimited storage

### **Manual Scaling**
- **MongoDB Atlas**: Upgrade cluster tier as needed
- **Lambda Memory**: Increase for better performance
- **CloudFront**: Add more edge locations if needed

---

## 🎯 Cost Optimization Tips

1. **Use Lambda Function URL** instead of API Gateway (if possible)
2. **Enable CloudFront caching** aggressively
3. **Use S3 Intelligent-Tiering** for uploads
4. **Set up S3 lifecycle policies** to archive old files
5. **Use ARM architecture** for Lambda (20% cheaper, if compatible)
6. **Reserve MongoDB Atlas capacity** (if predictable traffic)
7. **Monitor and optimize Lambda memory** (right-size)
8. **Use CloudWatch Insights** to find expensive operations
9. **Enable Lambda provisioned concurrency** only if needed (reduces cold starts)
10. **Use API Gateway caching** for frequently accessed data

---

## 🔄 Migration Path

### **From Local Development to Production**

1. **Development**: Keep local setup
2. **Staging**: Deploy to AWS with minimal resources
3. **Production**: Full deployment with monitoring

### **Rollback Strategy**

1. **Frontend**: Keep previous S3 versions, switch CloudFront origin
2. **Backend**: Use Lambda versions/aliases for instant rollback
3. **Database**: MongoDB Atlas automated backups

---

## 📝 Next Steps

1. **Review and approve this plan**
2. **Set up AWS account** (if not already)
3. **Create infrastructure** using AWS CDK or Terraform (recommended)
4. **Test deployment** in staging environment
5. **Migrate data** from local MongoDB to Atlas
6. **Deploy to production**
7. **Monitor and optimize**

---

## ❓ Questions to Consider

1. **Domain**: Do you have a custom domain? (2n1.com, etc.)
2. **Traffic Expectations**: What's the expected user base?
3. **Budget**: What's the monthly budget limit?
4. **Compliance**: Any specific compliance requirements?
5. **Backup Strategy**: How often should backups run?
6. **Disaster Recovery**: What's the RTO/RPO requirement?

---

## 📚 Additional Resources

- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [MongoDB Atlas Pricing](https://www.mongodb.com/pricing)
- [CloudFront Pricing](https://aws.amazon.com/cloudfront/pricing/)
- [S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Mangum (FastAPI to Lambda)](https://mangum.io/)

---

**Ready to proceed? Let me know which components you'd like to prioritize and any questions you have!**

