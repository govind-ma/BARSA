# S3-Compatible Storage Provider Guide

## 1. Supported Providers

The `S3StorageAdapter` provides native integration with any standard S3-compatible object storage service:
- **AWS S3**
- **MinIO** (Self-hosted or Kubernetes)
- **Cloudflare R2**
- **Ceph Object Gateway (RADOSGW)**
- **Backblaze B2** (via S3 endpoint)
- **Google Cloud Storage** (via XML API / interoperability)

---

## 2. Configuration & Registration

### Via REST API
```bash
POST /api/v1/sync/projects/proj-123/remotes
Content-Type: application/json

{
  "name": "aws-production",
  "provider_type": "s3",
  "s3_bucket_name": "my-company-barsa-storage",
  "s3_region": "us-east-1",
  "s3_endpoint_url": "https://s3.us-east-1.amazonaws.com",
  "s3_prefix": "teams/ai-core/proj-123",
  "s3_access_key": "AKIAIOSFODNN7EXAMPLE",
  "s3_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "encryption_enabled": true
}
```

### MinIO Local Development Setup
```bash
POST /api/v1/sync/projects/proj-123/remotes
Content-Type: application/json

{
  "name": "minio-local",
  "provider_type": "s3",
  "s3_bucket_name": "barsa-dev",
  "s3_endpoint_url": "http://127.0.0.1:9000",
  "s3_region": "us-east-1",
  "s3_access_key": "minioadmin",
  "s3_secret_key": "minioadmin",
  "encryption_enabled": false
}
```

---

## 3. Recommended IAM Bucket Policy

For maximum security, configure your IAM user or role with least-privilege permissions scoped only to the project prefix:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BarsaBucketList",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::my-company-barsa-storage",
      "Condition": {
        "StringLike": {
          "s3:prefix": "teams/ai-core/proj-123/*"
        }
      }
    },
    {
      "Sid": "BarsaObjectOps",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::my-company-barsa-storage/teams/ai-core/proj-123/*"
    }
  ]
}
```

---

## 4. Key Prefixes and Multi-Tenancy

Using `s3_prefix`, multiple projects or workspaces can share a single S3 bucket without collision:

```
my-company-barsa-storage/
├── workspace-alpha/
│   ├── proj-frontend/
│   │   ├── repository.json
│   │   ├── refs/main.json
│   │   └── objects/sha256/...
│   └── proj-backend/
│       ├── repository.json
│       ├── refs/main.json
│       └── objects/sha256/...
```

---

## 5. Optimistic Concurrency with S3 ETags

When `update_branch_ref` is executed, the adapter inspects the existing S3 object's ETag. If `expected_etag` does not match the observed remote ETag, a `ConflictError` is raised immediately, preventing concurrent overwrite anomalies.
