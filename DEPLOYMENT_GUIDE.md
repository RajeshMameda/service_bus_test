# Quick Deployment Guide - Your Existing Azure Resources

This guide is customized for your existing Azure resources.

---

## Your Azure Resources

- **Resource Group:** `geo_data`
- **Function App:** `service-bus-test`
- **Service Bus Namespace:** `service-bus-test-python`
- **PostgreSQL Server:** `postgresql-geo-test-dev`
- **Database:** `ordersdb`

---

## Step 1: Configure Function App Settings

Set the required environment variables in your existing Function App:

```bash
# Set Service Bus connection string
az functionapp config appsettings set \
  --name service-bus-test \
  --resource-group geo_data \
  --settings ServiceBusConnection="Endpoint=sb://service-bus-test-python.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=<your-key>"

# Set PostgreSQL connection settings
az functionapp config appsettings set \
  --name service-bus-test \
  --resource-group geo_data \
  --settings \
    PGHOST="postgresql-geo-test-dev.postgres.database.azure.com" \
    PGDATABASE="ordersdb" \
    PGUSER="<your-postgres-admin-user>" \
    PGPASSWORD="<your-postgres-password>" \
    PGPORT="5432" \
    PGSSLMODE="require"

# Set queue names (if different from defaults)
az functionapp config appsettings set \
  --name service-bus-test \
  --resource-group geo_data \
  --settings \
    ORDERS_QUEUE_NAME="orders" \
    CONFIRMATIONS_QUEUE_NAME="order-confirmations"
```

### Get Service Bus Connection String
```bash
az servicebus namespace authorization-rule keys list \
  --resource-group geo_data \
  --namespace-name service-bus-test-python \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv
```

---

## Step 2: Set Up Azure DevOps

### 2.1 Create Azure DevOps Project
1. Go to https://dev.azure.com
2. Create new project: `ServiceBusFunctionApp`

### 2.2 Connect GitHub
1. **Project Settings** → **Service connections** → **New service connection**
2. Select **GitHub** → **Next**
3. Choose **Grant authorization**
4. Authorize Azure Pipelines
5. Name: `GitHub-Connection`
6. Click **Save**

### 2.3 Create Azure Service Connection
1. **Project Settings** → **Service connections** → **New service connection**
2. Select **Azure Resource Manager** → **Next**
3. Choose **Service principal (automatic)** → **Next**
4. Configure:
   - **Scope level:** Subscription
   - **Subscription:** Select your subscription
   - **Resource group:** `geo_data`
   - **Service connection name:** `Azure-Service-Connection`
   - **Grant access permission to all pipelines:** ✅
5. Click **Save**

---

## Step 3: Create Pipeline

### 3.1 Verify Pipeline Configuration
The `azure-pipelines.yml` is already configured with your resources:
- Function App: `service-bus-test`
- Resource Group: `geo_data`

### 3.2 Create Pipeline in Azure DevOps
1. **Pipelines** → **New pipeline**
2. Select **GitHub**
3. Select your repository
4. Select **Existing Azure Pipelines YAML file**
5. Choose `/azure-pipelines.yml`
6. Click **Continue**
7. Review and click **Run**

---

## Step 4: Verify Deployment

After pipeline succeeds:

```bash
# Get Function App URL
az functionapp show \
  --name service-bus-test \
  --resource-group geo_data \
  --query defaultHostName -o tsv

# Test POST endpoint (send order)
curl -X POST https://service-bus-test.azurewebsites.net/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-001",
    "customer_id": "cust-001",
    "product_id": "prod-001",
    "quantity": 3,
    "price": 49.99
  }'

# Test GET endpoint (retrieve order)
curl https://service-bus-test.azurewebsites.net/api/orders/test-001
```

---

## Step 5: Monitor Function App

### View Logs
```bash
# Stream logs
az webapp log tail \
  --name service-bus-test \
  --resource-group geo_data
```

### Azure Portal
1. Go to Azure Portal → Function Apps → `service-bus-test`
2. **Monitor** → **Log stream**
3. Watch for incoming requests and Service Bus triggers

---

## CI/CD Workflow

```
Push to GitHub (main/dev branch)
         ↓
Azure DevOps Pipeline triggers
         ↓
Build Stage:
  - Install Python 3.11
  - Install dependencies from requirements.txt
  - Create deployment package
         ↓
Deploy Stage:
  - Deploy to service-bus-test Function App
  - Function App restarts with new code
         ↓
Functions are live:
  - POST /api/orders (send order to Service Bus)
  - GET /api/orders/{order_id} (retrieve from PostgreSQL)
  - ordersprocessor (Service Bus trigger)
  - confirmationsprocessor (Service Bus trigger)
```

---

## Troubleshooting

### Check Function App Status
```bash
az functionapp show \
  --name service-bus-test \
  --resource-group geo_data \
  --query state -o tsv
```

### View Application Settings
```bash
az functionapp config appsettings list \
  --name service-bus-test \
  --resource-group geo_data \
  --output table
```

### Restart Function App
```bash
az functionapp restart \
  --name service-bus-test \
  --resource-group geo_data
```

---

## Next Steps

1. ✅ Configure app settings (Step 1)
2. ✅ Set up Azure DevOps (Step 2)
3. ✅ Create pipeline (Step 3)
4. ✅ Push to GitHub → Pipeline auto-deploys
5. ✅ Test endpoints (Step 4)
6. ✅ Monitor logs (Step 5)

Your Function App is ready for CI/CD deployment! 🚀
