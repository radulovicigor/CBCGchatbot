#!/bin/bash
# Azure deployment script

set -e

echo "========================================"
echo "  CBCG Chatbot - Azure Deployment"
echo "========================================"
echo ""

# Provera Azure CLI
if ! command -v az &> /dev/null; then
    echo "[ERROR] Azure CLI nije instaliran!"
    echo "Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Provera login-a
if ! az account show &> /dev/null; then
    echo "[ERROR] Nisi ulogovan u Azure!"
    echo "Run: az login"
    exit 1
fi

read -p "Unesi resource group name (npr. rg-cbcgbot-dev): " RG_NAME
read -p "Unesi location (npr. northeurope): " LOCATION
read -p "Unesi environment (dev/prod): " ENV

# Kreiranje resource group
echo "[1/5] Kreiranje resource group..."
az group create --name "$RG_NAME" --location "$LOCATION"

# Bicep deployment
echo "[2/5] Bicep deployment..."
az deployment group create \
  --resource-group "$RG_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters environment="$ENV"

# Kreiranje indeksa
echo "[3/5] Kreiranje Search indeksa..."
echo "TODO: Connect to Azure and run:"
echo "  from apps.ingest.push_to_search import create_index_faq, create_index_news"
echo "  create_index_faq()"
echo "  create_index_news()"

# Deploy API
echo "[4/5] Deploying API..."
cd apps/api
az webapp up \
  --name "app-cbcgbot-$ENV" \
  --runtime "PYTHON:3.11" \
  --resource-group "$RG_NAME"
cd ../..

# Deploy Functions
echo "[5/5] Deploying Functions..."
cd apps/functions
func azure functionapp publish "func-cbcgbot-$ENV"
cd ../..

echo ""
echo "✅ Deployment zavrsen!"
echo ""
echo "NEXT STEPS:"
echo "1. Configure environment variables in Azure Portal"
echo "2. Upload SEPA_QnA.pdf to Azure Blob Storage"
echo "3. Run ingest: python -m apps.ingest.push_to_search"
echo "4. Test: curl https://app-cbcgbot-$ENV.azurewebsites.net/health"

