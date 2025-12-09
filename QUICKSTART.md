# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker and Docker Compose installed
- Azure OpenAI resource with GPT-4 or GPT-4o deployment
- Excel file with customer data

### Step 1: Clone and Configure

```bash
# Navigate to project directory
cd compliance-ai-service

# Copy environment template
cp .env.example .env

# Edit .env with your Azure OpenAI credentials
# Required values:
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_DEPLOYMENT_RISK
```

### Step 2: Start the Service

```bash
# Build and start with Docker Compose
docker compose up --build

# Wait for "Application startup complete" message
# Service will be available at http://localhost:8000
```

### Step 3: Test the API

Open another terminal and test with curl:

```bash
curl -X POST "http://localhost:8000/risk/bulk-excel?upload_country=UZ" \
  -F "file=@your-customer-list.xlsx"
```

Or use the interactive API docs:
```
http://localhost:8000/docs
```

## 📋 Excel File Requirements

Your Excel file must have a "Customers" sheet with these columns:

**Minimum Required:**
- CustomerNo, DocumentName, MainAccount
- District, Region, Locality, Street
- Citizenship, Nationality, BirthCountry
- PassportIssuerCode, PassportIssuerPlace
- RegDocType, RegDocNum, ResidentStatus
- (and other standard fields - see EXCEL_TEMPLATE_SPEC.md)

**Optional (for enhanced detection):**
- Email
- IPAddress, IPCountry, IsVPN
- DeviceId
- Occupation
- BirthDate

## 📊 Understanding the Response

The API returns JSON with:

```json
{
  "report_id": "rpt_2025_12_09_143045_a1b2",
  "generated_at": "2025-12-09T14:30:45Z",
  
  "file": {
    "filename": "customers.xlsx",
    "rows_processed": 10,
    "validation": { "status": "OK" }
  },
  
  "summary": {
    "total_customers": 10,
    "risk_distribution": {
      "LOW": 7,
      "MEDIUM": 0,
      "HIGH": 2,
      "CRITICAL": 1
    },
    "avg_score": 32,
    "top_risk_drivers": [
      "FATF high-risk jurisdictions",
      "High-risk occupations"
    ]
  },
  
  "customers": [
    {
      "customerNo": "CUST-001",
      "fullName": "John Smith",
      "risk": {
        "score": 85,
        "riskLevel": "CRITICAL",
        "confidence": 0.88,
        "riskDrivers": [
          "Customer from FATF high-risk jurisdiction",
          "High-risk business category"
        ]
      },
      "tags": [...],
      "recommendedActions": [...]
    }
  ]
}
```

## 🎯 Risk Levels Explained

| Level | Score | Meaning | Action |
|-------|-------|---------|--------|
| **LOW** | 0-24 | Standard risk | Standard monitoring |
| **MEDIUM** | 25-49 | Moderate risk | Enhanced monitoring with alerts |
| **HIGH** | 50-74 | High risk | Enhanced due diligence |
| **CRITICAL** | 75-100 | Critical risk | Immediate escalation to compliance |

## 🔧 Common Issues

### "Azure OpenAI endpoint or API key is missing"
**Solution**: Check your .env file has correct values

### "Invalid file format"
**Solution**: Ensure you're uploading .xlsx or .xls file

### "Missing required columns"
**Solution**: Check error message for specific columns, add them to your Excel

### "Pydantic validation errors"
**Solution**: This should be fixed in the latest version. If you still see this:
1. Verify you're using GPT-4 or GPT-4o (not GPT-3.5)
2. Check Docker logs: `docker compose logs ai-service`
3. The system has fallback logic if LLM fails

## 📖 Next Steps

1. **Review Full Documentation**: See `IMPLEMENTATION_GUIDE.md`
2. **Excel Template**: See `EXCEL_TEMPLATE_SPEC.md`
3. **Customize Risk Rules**: Edit `bulk_risk_engine.py`
4. **Tune Azure OpenAI Prompts**: Edit `agent_risk_explainer.py`

## 🛠️ Development Mode

To make code changes:

```bash
# Edit files in ai-service/app/

# Restart service to apply changes
docker compose restart ai-service

# Or rebuild if you changed requirements.txt
docker compose up --build
```

## 🔍 View Logs

```bash
# All services
docker compose logs -f

# Just AI service
docker compose logs -f ai-service

# Last 100 lines
docker compose logs --tail=100 ai-service
```

## 🧪 Testing Different Scenarios

### Test Low Risk Customer
Create Excel with:
- Citizenship: UZB (Uzbekistan)
- MainAccount: retail_banking
- ResidentStatus: RESIDENT
- No VPN, normal email

### Test High Risk Customer
Create Excel with:
- Citizenship: IRN (Iran)
- MainAccount: international_money_service_business
- ResidentStatus: NON_RESIDENT
- IsVPN: Y

### Test Critical Risk Customer
Create Excel with:
- Citizenship: PRK (North Korea)
- MainAccount: front_company_trader
- Email: suspicious@tempmail.com
- IsVPN: Y
- DeviceId: (same as another customer)

## 💡 Tips

1. **Batch Size**: Process 10-100 customers per file for optimal performance
2. **Azure OpenAI Costs**: Each customer = ~2 API calls. Monitor usage in Azure Portal
3. **Rate Limits**: Azure OpenAI has rate limits. Add delays if processing many files
4. **Device Tracking**: Resets per file upload (not persistent across batches)

## 📞 Support

If issues persist:
1. Check `IMPLEMENTATION_GUIDE.md` troubleshooting section
2. Review Docker logs for detailed errors
3. Verify Azure OpenAI deployment is working in Azure Portal
4. Test with minimal Excel file (1-2 rows) first

## ✅ Checklist

Before going to production:

- [ ] Azure OpenAI credentials configured
- [ ] Tested with sample data
- [ ] Reviewed risk scoring logic
- [ ] Customized high-risk categories for your region
- [ ] Updated FATF lists if needed
- [ ] Set up proper logging/monitoring
- [ ] Documented any customizations
- [ ] Load tested with expected file sizes
- [ ] Set up backup/disaster recovery
- [ ] Reviewed data privacy/compliance requirements
