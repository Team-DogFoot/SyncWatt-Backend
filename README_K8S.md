# SyncWatt K3s Deployment Guide: Secrets & ArgoCD

This guide explains how to manage secrets and deploy the application using ArgoCD on a K3s cluster.

## 1. Secret Management

We use [SealedSecrets](https://github.com/bitnami-labs/sealed-secrets) to safely store sensitive information in Git.

### Prerequisites
- `kubeseal` CLI installed on your local machine.
- SealedSecrets controller installed in the K3s cluster.

### Step 1: Create a Local Secret (Dry-run)
First, create a standard Kubernetes Secret locally without applying it to the cluster.

> **CRITICAL:** Ensure `secret.yaml` is added to your `.gitignore` file. NEVER commit unencrypted secrets to Git.

```bash
kubectl create secret generic syncwatt-secret \
  --from-literal=TELEGRAM_BOT_TOKEN='your-telegram-token' \
  --from-literal=WEBHOOK_SECRET_TOKEN='your-webhook-secret' \
  --from-literal=GCP_SA_KEY='your-gcp-service-account-json-string' \
  --dry-run=client -o yaml > secret.yaml
```

### Step 2: Seal the Secret
Use `kubeseal` to encrypt the `secret.yaml` file. The resulting `sealed-secret.yaml` is safe to commit to Git.

```bash
kubeseal --format yaml < secret.yaml > sealed-secret.yaml
```

### Step 3: Apply the SealedSecret
Apply the sealed secret to the cluster. The SealedSecrets controller will automatically decrypt it and create a regular Secret.

```bash
kubectl apply -f sealed-secret.yaml -n syncwatt-prod
```

## 2. ArgoCD Application

To deploy the application via ArgoCD, use the manifest provided in `argocd/syncwatt-app.yaml`.

### Applying the ArgoCD Application
```bash
kubectl apply -f argocd/syncwatt-app.yaml -n argocd
```

This will create the `syncwatt-prod` application in ArgoCD, which tracks the manifests in the specified repository.
