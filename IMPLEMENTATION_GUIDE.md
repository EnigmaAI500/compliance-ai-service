# Compliance AI Service - Implementation Guide

## Overview

This is a comprehensive compliance risk assessment service that analyzes bulk customer data from Excel files and provides detailed risk scoring, sanctions screening, and recommended actions using Azure OpenAI.

## Key Features

### ✅ Implemented Features

1. **4-Band Risk Scoring System**
   - LOW (0-24): Standard monitoring
   - MEDIUM (25-49): Enhanced monitoring with alerts
   - HIGH (50-74): Enhanced due diligence required
   - CRITICAL (75-100): Immediate escalation to compliance

2. **Multi-Factor Risk Assessment**
   - **FATF Country Risk**: Detects customers from high-risk and grey-list jurisdictions
   - **Sanctions Screening**: Name-based matching with support for birthdate/birthplace
   - **PEP Detection**: Identifies Politically Exposed Persons
   - **VPN & IP Mismatch**: Detects VPN usage and foreign IP addresses
   - **Device Reuse**: Tracks device IDs across multiple customers
   - **High-Risk Occupations**: Identifies cash-intensive businesses, front companies, money service businesses
   - **Email Domain Risk**: Detects disposable and high-risk email domains

3. **Azure OpenAI Integration**
   - Structured JSON responses for consistent output
   - Enhanced risk driver explanations
   - Intelligent tagging with evidence
   - Context-aware recommended actions
   - Fallback to deterministic rules if LLM fails

4. **Sanctions Matching Enhancement**
   - Name similarity matching (existing + enhanced)
   - Birth date exact matching (ready for enhanced data)
   - Birth country/place matching (ready for enhanced data)
   - Confidence scoring based on multiple factors

5. **Comprehensive Output Format**
   - Report metadata with validation status
   - Batch summary with risk distribution
   - Per-customer detailed risk assessment
   - Structured tags with evidence
   - Actionable recommendations by urgency

## Architecture

```
Excel Upload → Parser → Risk Engine → Sanctions Matcher → Azure OpenAI → JSON Response
                ↓
         Device Tracking
         VPN Detection
         Occupation Risk
         FATF Check
         PEP Check
```

## API Endpoint

### POST `/risk/bulk-excel`

Upload an Excel file with customer data and receive comprehensive risk analysis.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Query Parameter: `upload_country` (optional, default: "UZ")
- Body: Excel file with "Customers" sheet

**Excel Required Columns:**
- CustomerNo
- DocumentName (Full Name)
- MainAccount (Business category)
- District, Region, Locality, Street
- Pinfl, ExpiryDate
- Nationality, NationalityDesc
- BirthCountry
- PassportIssuerCode, PassportIssuerPlace
- Citizenship, CitizenshipDesc
- RegDocType, RegDocNum, RegDocSerialNum, RegPinfl
- Lang, AddressCode, ResidentStatus

**Excel Optional Columns (for enhanced detection):**
- Email
- IPAddress
- IPCountry
- IsVPN (Y/N)
- DeviceId
- Occupation
- BirthDate (YYYY-MM-DD for sanctions matching)
- RiskFlag, RiskScore, RiskReason (historical data)

**Response:** JSON with structure matching `example-response-body.json`

## Setup Instructions

### 1. Azure OpenAI Setup

Create an Azure OpenAI resource and deploy a GPT-4 or GPT-4o model:

1. Go to Azure Portal
2. Create an "Azure OpenAI" resource
3. Navigate to "Model deployments"
4. Deploy a GPT-4 or GPT-4o model
5. Note down:
   - Endpoint URL
   - API Key
   - Deployment name

### 2. Environment Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_RISK=gpt-4o
```

### 3. Docker Setup

Build and run with Docker Compose:

```bash
docker compose up --build
```

The service will be available at `http://localhost:8000`

### 4. Test the API

Using curl:
```bash
curl -X POST "http://localhost:8000/risk/bulk-excel?upload_country=UZ" \
  -F "file=@your-customer-list.xlsx"
```

Using Python:
```python
import requests

url = "http://localhost:8000/risk/bulk-excel?upload_country=UZ"
files = {"file": open("customer_list.xlsx", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

## Risk Scoring Details

### Score Calculation

Each customer receives a score from 0-100 based on multiple factors:

| Factor | Max Score | Description |
|--------|-----------|-------------|
| **Sanctions** | 50 | FATF blacklist countries, sanctions matches |
| **PEP** | 30 | Politically Exposed Person status |
| **Profile** | 40 | High-risk occupations and business categories |
| **Digital** | 30 | VPN usage, IP mismatches, email risk |
| **Device** | 20 | Device reuse patterns |

**Special Cases:**
- Local blacklist → Immediate CRITICAL (100)
- Sanctions match with >80% confidence → Minimum 90 (CRITICAL)

### Risk Drivers Examples

The system identifies specific risk factors:
- "Customer from FATF high-risk jurisdiction (Iran)"
- "High-risk business category: international money service business"
- "VPN usage detected"
- "Device reused by 5 customers"
- "IP country (RU) mismatch with citizenship (UZ)"
- "Email domain considered high-risk"

### Tag Codes

- `FATF_HIGH_RISK`: FATF blacklist country
- `FATF_GREY_LIST`: FATF grey list country
- `SANCTIONS_MATCH`: Matched sanctions database
- `PEP_MATCH`: Politically Exposed Person
- `HIGH_RISK_OCCUPATION`: Cash-intensive or front company business
- `VPN_USAGE`: VPN detected
- `COUNTRY_MISMATCH`: IP/citizenship mismatch
- `DEVICE_REUSE`: Device shared across customers
- `EMAIL_HIGH_RISK`: Suspicious email domain
- `LOCAL_BLACKLIST`: In local blacklist

## Azure OpenAI Prompts

### Risk Explanation Prompt

The system uses a comprehensive prompt that instructs Azure OpenAI to:
1. Preserve deterministic scores from the rule engine
2. Generate human-readable risk drivers
3. Create structured tags with evidence objects
4. Suggest appropriate actions based on risk level

Key features:
- Enforces strict JSON output format
- Validates all required Pydantic fields
- Provides fallback to deterministic rules
- Maintains data consistency

### Sanctions Decision Prompt

Conservative approach for sanctions matching:
- Requires strong evidence (name + birthdate + country)
- Returns confidence score and detailed reasoning
- Only confirms match when confidence ≥ 80%

## High-Risk Categories

### FATF Blacklist Countries
Iran (IRN), North Korea (PRK), Syria (SYR), etc.

### FATF Grey List Countries  
(Enhanced monitoring jurisdictions)

### High-Risk Occupations
- Front company trader
- International money service business
- Cash-intensive business
- Casino operations
- Cryptocurrency services
- Money exchange
- Real estate
- Precious metals dealers
- Art dealers

### High-Risk Email Domains
- Country TLDs: .ru, .ir, .kp, .sy
- Disposable: tempmail, guerrillamail, 10minutemail

## Troubleshooting

### Common Issues

**1. Pydantic Validation Errors**
- **Cause**: Azure OpenAI returning incorrect JSON structure
- **Solution**: The code now includes validation and fallback logic
- **Check**: Ensure AZURE_OPENAI_DEPLOYMENT_RISK uses GPT-4 or GPT-4o

**2. 400 Bad Request**
- **Cause**: Missing required Excel columns
- **Solution**: Ensure your Excel has all required columns
- **Check**: Review error message for specific missing columns

**3. Azure OpenAI Connection Errors**
- **Cause**: Invalid endpoint or API key
- **Solution**: Verify .env configuration
- **Check**: Test credentials in Azure Portal

**4. Device Reuse Not Detected**
- **Cause**: DeviceId column missing or empty
- **Solution**: Add DeviceId column to Excel
- **Note**: Device tracking resets per batch

### Debugging

Enable detailed logging:
```python
# In logging_config.py, set level to DEBUG
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check Docker logs:
```bash
docker compose logs -f ai-service
```

## Future Enhancements

### Planned Features

1. **Enhanced Sanctions Data**
   - Add birthdate and birthplace to sanctions records
   - Implement fuzzy date matching
   - Add more international sanctions lists

2. **Real-time IP Geolocation**
   - Integrate with MaxMind or similar service
   - Accurate IP country detection
   - VPN detection service integration

3. **ML-Based Risk Scoring**
   - Train custom ML model on historical data
   - Combine with rule-based approach
   - Adaptive risk thresholds

4. **Batch Processing Optimization**
   - Parallel processing of customers
   - Caching for repeated Azure OpenAI calls
   - Streaming responses for large files

5. **Enhanced Reporting**
   - PDF export generation
   - Excel export with formatting
   - Dashboard UI

## Code Structure

```
ai-service/app/
├── main.py                      # FastAPI endpoints
├── bulk_orchestrator.py         # Main orchestration logic
├── bulk_risk_engine.py          # Enhanced risk scoring engine
├── bulk_excel_parser.py         # Excel parsing with validation
├── bulk_sanctions_matcher.py    # Enhanced sanctions matching
├── agent_risk_explainer.py      # Azure OpenAI risk explanation
├── agent_sanctions_decision.py  # Azure OpenAI sanctions review
├── azure_openai_client.py       # Azure OpenAI client wrapper
├── bulk_models.py              # Pydantic models
├── pure_risk_scorer.py         # Core risk rules
└── logging_config.py           # Logging configuration
```

## License

See LICENSE file for details.

## Support

For issues or questions:
1. Check this README
2. Review error logs
3. Verify Azure OpenAI configuration
4. Ensure Excel format matches requirements
