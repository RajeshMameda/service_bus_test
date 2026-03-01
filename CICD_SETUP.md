# Azure DevOps CI/CD Pipeline Setup Guide

This guide walks you through setting up a CI/CD pipeline to deploy your Azure Function App from GitHub to Azure using Azure DevOps.

---

## Prerequisites

- Azure subscription
- Azure Function App created (or will create)
- GitHub repository with your code
- Azure DevOps organization (free tier available)

---

## Step 1: Create Azure Function App (if not exists)

```bash
# Login to Azure
az login

# Create resource group (if not exists)
az group create --name rg-servicebus-functions --location eastus

# Create storage account for Function App
az storage account create \
  --name stfuncservicebus \
  --resource-group rg-servicebus-functions \
  --location eastus \
  --sku Standard_LRS

# Create Function App (Linux, Python 3.11)
az functionapp create \
  --name func-servicebus-orders \
  --resource-group rg-servicebus-functions \
  --storage-account stfuncservicebus \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux
```

**Note:** Replace `func-servicebus-orders` with your desired Function App name (must be globally unique).

---

## Step 2: Set Up Azure DevOps Project

### 2.1 Create Azure DevOps Organization (if needed)
1. Go to https://dev.azure.com
2. Sign in with your Microsoft account
3. Click **+ New organization**
4. Follow the prompts to create your organization

### 2.2 Create a New Project
1. In your Azure DevOps organization, click **+ New project**
2. Enter project details:
   - **Project name:** `ServiceBusFunctionApp`
   - **Visibility:** Private
   - **Version control:** Git
3. Click **Create**

---

## Step 3: Connect GitHub to Azure DevOps

### Option A: GitHub Service Connection (Recommended)

1. In Azure DevOps, go to **Project Settings** (bottom left)
2. Under **Pipelines**, click **Service connections**
3. Click **New service connection**
4. Select **GitHub** → **Next**
5. Choose **Grant authorization** or **Personal access token**
   - **Grant authorization:** Easier, OAuth-based
   - **Personal access token:** More control
6. Authorize Azure Pipelines to access your GitHub account
7. Name the connection: `GitHub-Connection`
8. Click **Save**

### Option B: Import Repository to Azure Repos

1. In Azure DevOps, go to **Repos** → **Files**
2. Click **Import** (if empty repo)
3. Enter your GitHub repository URL
4. Click **Import**

---

## Step 4: Create Azure Service Connection

This allows Azure DevOps to deploy to your Azure subscription.

1. In Azure DevOps, go to **Project Settings** → **Service connections**
2. Click **New service connection**
3. Select **Azure Resource Manager** → **Next**
4. Choose **Service principal (automatic)** → **Next**
5. Configure:
   - **Scope level:** Subscription
   - **Subscription:** Select your Azure subscription
   - **Resource group:** `rg-servicebus-functions` (or leave empty for subscription-level)
   - **Service connection name:** `Azure-Service-Connection`
   - **Grant access permission to all pipelines:** ✅ Check this
6. Click **Save**

---

## Step 5: Configure Application Settings in Azure

Your Function App needs environment variables for Service Bus and PostgreSQL.

```bash
# Set Service Bus connection string
az functionapp config appsettings set \
  --name func-servicebus-orders \
  --resource-group rg-servicebus-functions \
  --settings ServiceBusConnection="<your-service-bus-connection-string>"

# Set PostgreSQL settings
az functionapp config appsettings set \
  --name func-servicebus-orders \
  --resource-group rg-servicebus-functions \
  --settings \
    PGHOST="<your-postgres-host>" \
    PGDATABASE="ordersdb" \
    PGUSER="<your-postgres-user>" \
    PGPASSWORD="<your-postgres-password>" \
    PGPORT="5432" \
    PGSSLMODE="require"

# Set queue names (optional, if different from defaults)
az functionapp config appsettings set \
  --name func-servicebus-orders \
  --resource-group rg-servicebus-functions \
  --settings \
    ORDERS_QUEUE_NAME="orders" \
    CONFIRMATIONS_QUEUE_NAME="order-confirmations"
```

**Security Best Practice:** Use Azure Key Vault for secrets:
```bash
# Create Key Vault
az keyvault create \
  --name kv-servicebus-func \
  --resource-group rg-servicebus-functions \
  --location eastus

# Add secrets
az keyvault secret set --vault-name kv-servicebus-func --name ServiceBusConnection --value "<connection-string>"
az keyvault secret set --vault-name kv-servicebus-func --name PGPassword --value "<password>"

# Grant Function App access to Key Vault
az functionapp identity assign --name func-servicebus-orders --resource-group rg-servicebus-functions
PRINCIPAL_ID=$(az functionapp identity show --name func-servicebus-orders --resource-group rg-servicebus-functions --query principalId -o tsv)
az keyvault set-policy --name kv-servicebus-func --object-id $PRINCIPAL_ID --secret-permissions get list

# Reference in app settings
az functionapp config appsettings set \
  --name func-servicebus-orders \
  --resource-group rg-servicebus-functions \
  --settings ServiceBusConnection="@Microsoft.KeyVault(SecretUri=https://kv-servicebus-func.vault.azure.net/secrets/ServiceBusConnection/)"
```

---

## Step 6: Update Pipeline Configuration

Edit `azure-pipelines.yml` in your repository:

```yaml
variables:
  azureSubscription: 'Azure-Service-Connection'  # Match your service connection name
  functionAppName: 'func-servicebus-orders'      # Your Function App name
  pythonVersion: '3.11'                          # Azure supports 3.9, 3.10, 3.11
```

**Important:** Azure Functions currently supports Python up to 3.11, not 3.14. The pipeline uses 3.11.

---

## Step 7: Create Pipeline in Azure DevOps

### 7.1 Create Pipeline
1. In Azure DevOps, go to **Pipelines** → **Pipelines**
2. Click **New pipeline** (or **Create Pipeline**)
3. Select **GitHub** (if using GitHub) or **Azure Repos Git**
4. Select your repository
5. Select **Existing Azure Pipelines YAML file**
6. Choose `/azure-pipelines.yml`
7. Click **Continue**

### 7.2 Review and Run
1. Review the pipeline YAML
2. Click **Run**
3. The pipeline will:
   - Install Python 3.11
   - Install dependencies from `requirements.txt`
   - Archive the `functionapp/` folder
   - Deploy to Azure Function App

---

## Step 8: Configure Branch Policies (Optional)

Protect your main branch and require PR builds:

1. Go to **Repos** → **Branches**
2. Click **...** next to `main` → **Branch policies**
3. Enable:
   - **Require a minimum number of reviewers:** 1
   - **Check for linked work items:** Optional
   - **Build validation:** Add your pipeline
4. Click **Save**

---

## Step 9: Monitor Deployments

### View Pipeline Runs
1. Go to **Pipelines** → **Pipelines**
2. Click on your pipeline
3. View run history and logs

### View Function App Logs
```bash
# Stream logs
az webapp log tail --name func-servicebus-orders --resource-group rg-servicebus-functions

# Or use Azure Portal
# Go to Function App → Monitor → Log stream
```

---

## Step 10: Test Deployment

After successful deployment:

```bash
# Get Function App URL
FUNCTION_URL=$(az functionapp show --name func-servicebus-orders --resource-group rg-servicebus-functions --query defaultHostName -o tsv)

# Test POST endpoint (send order)
curl -X POST https://$FUNCTION_URL/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-123",
    "customer_id": "cust-456",
    "product_id": "prod-789",
    "quantity": 5,
    "price": 99.99
  }'

# Test GET endpoint (retrieve order)
curl https://$FUNCTION_URL/api/orders/test-123
```

---

## Troubleshooting

### Pipeline fails at deployment
- Verify service connection has correct permissions
- Check Function App name is correct
- Ensure resource group exists

### Function App doesn't start
- Check Application Settings are configured
- Verify Service Bus connection string is valid
- Check PostgreSQL connection settings
- Review Function App logs in Azure Portal

### Python version mismatch
- Local development uses Python 3.14
- Azure Functions supports up to Python 3.11
- Code is compatible (psycopg works on both)

---

## CI/CD Workflow Summary

```
Developer pushes to GitHub (main/dev branch)
         ↓
Azure DevOps Pipeline triggers
         ↓
Build Stage:
  - Install Python 3.11
  - Install dependencies
  - Run tests (optional)
  - Create deployment package
         ↓
Deploy Stage:
  - Deploy to Azure Function App
  - Function App starts with new code
         ↓
Service Bus triggers functions automatically
PostgreSQL stores order data
```

---

## Next Steps

1. **Add Tests:** Create unit tests in `functionapp/tests/`
2. **Add Environments:** Create dev/staging/prod environments
3. **Add Approval Gates:** Require manual approval before production
4. **Monitor with Application Insights:** Enable monitoring and alerts
5. **Set up Alerts:** Configure alerts for failures

---

## Additional Resources

- [Azure Functions Python Developer Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure DevOps Pipelines Documentation](https://learn.microsoft.com/en-us/azure/devops/pipelines/)
- [Azure Function App Deployment](https://learn.microsoft.com/en-us/azure/azure-functions/functions-deployment-technologies)
