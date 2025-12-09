# Compliance AI Service

Enterprise-grade AML/CFT Risk Assessment Service with Azure OpenAI integration, sanctions matching, FATF country risk analysis, VPN detection, device tracking, and comprehensive compliance checks.

## 🌟 Features

- **4-Band Risk Scoring**: LOW, MEDIUM, HIGH, CRITICAL with deterministic rules
- **Azure OpenAI Integration**: GPT-4 powered risk analysis and explanations
- **Sanctions Screening**: Name, birthdate, and birthplace matching
- **FATF Country Risk**: Automatic detection of high-risk and grey-list jurisdictions
- **VPN & IP Detection**: Identify VPN usage and country mismatches
- **Device Reuse Tracking**: Detect devices shared across multiple customers
- **High-Risk Occupations**: Front companies, cash-intensive businesses, MSBs
- **Bulk Excel Processing**: Analyze hundreds of customers in one API call
- **Structured JSON Output**: Consistent, Pydantic-validated responses

## 📚 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get up and running in 5 minutes
- **[Implementation Guide](IMPLEMENTATION_GUIDE.md)** - Comprehensive technical documentation
- **[Excel Template Specification](EXCEL_TEMPLATE_SPEC.md)** - Input file format and requirements
- **[Example Response](example-response-body.json)** - Sample API output

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Azure OpenAI resource with GPT-4 or GPT-4o deployment
- At least 4GB RAM available

### 1. Configure Azure OpenAI

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_DEPLOYMENT_RISK=gpt-4o
```

### 2. Start the Service

```bash
docker compose up --build
```

Service will be available at `http://localhost:8000`

### 3. Upload Excel File

```bash
curl -X POST "http://localhost:8000/risk/bulk-excel?upload_country=UZ" \
  -F "file=@your-customer-list.xlsx"
```

Or use the interactive API docs: `http://localhost:8000/docs`

## 📊 Risk Scoring System

### 4-Band Risk Levels

| Level | Score Range | Action Required |
|-------|-------------|-----------------|
| **LOW** | 0-24 | Standard monitoring |
| **MEDIUM** | 25-49 | Enhanced monitoring with alerts |
| **HIGH** | 50-74 | Enhanced due diligence |
| **CRITICAL** | 75-100 | Immediate escalation to compliance |

### Risk Factors Analyzed

| Factor | Weight | Examples |
|--------|--------|----------|
| **Sanctions** | Up to 50 | FATF blacklist countries, sanctions matches |
| **PEP** | Up to 30 | Politically Exposed Persons |
| **Profile** | Up to 40 | High-risk occupations, cash-intensive businesses |
| **Digital** | Up to 30 | VPN usage, IP mismatches, suspicious email domains |
| **Device** | Up to 20 | Device reuse across multiple customers |

**Special Rules:**
- Local blacklist → Automatic CRITICAL (100)
- Sanctions match (>80% confidence) → Minimum 90 (CRITICAL)

## 🏗️ Architecture

```
Excel Upload
    ↓
Excel Parser (validation)
    ↓
Risk Engine (deterministic scoring)
    ├→ FATF Country Risk
    ├→ PEP Detection
    ├→ Occupation Risk
    ├→ VPN/IP Detection
    └→ Device Tracking
    ↓
Sanctions Matcher (name + birthdate)
    ↓
Azure OpenAI (GPT-4)
    ├→ Risk Explanation
    ├→ Tags with Evidence
    └→ Recommended Actions
    ↓
JSON Response (Pydantic validated)
```

## 📋 Excel File Format

See [EXCEL_TEMPLATE_SPEC.md](EXCEL_TEMPLATE_SPEC.md) for complete specification.

### Required Columns (23 fields)
CustomerNo, DocumentName, MainAccount, District, Region, Citizenship, etc.

### Optional Columns (Enhanced Detection)
- **Email** - For email domain risk analysis
- **IPAddress**, **IPCountry** - For geolocation checks
- **IsVPN** (Y/N) - VPN detection flag
- **DeviceId** - For device reuse tracking
- **Occupation** - For occupation-based risk
- **BirthDate** - For enhanced sanctions matching

## 🔧 Configuration

### Environment Variables

```env
# Azure OpenAI (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_RISK=gpt-4o

# Optional
DATABASE_URL=postgresql://user:pass@localhost:5432/db
LOG_LEVEL=INFO
```

See `.env.example` for full configuration options.

## 📖 API Documentation

### Response Structure

```json
{
  "report_id": "rpt_2025_12_09_143045_a1b2",
  "generated_at": "2025-12-09T14:30:45Z",
  "file": {
    "filename": "customers.xlsx",
    "rows_processed": 10,
    "validation": {"status": "OK"}
  },
  "summary": {
    "total_customers": 10,
    "risk_distribution": {"LOW": 7, "HIGH": 2, "CRITICAL": 1},
    "avg_score": 32,
    "top_risk_drivers": [...]
  },
  "customers": [
    {
      "customerNo": "CUST-001",
      "risk": {
        "score": 85,
        "riskLevel": "CRITICAL",
        "confidence": 0.88,
        "riskDrivers": [...],
        "breakdown": {...}
      },
      "tags": [...],
      "recommendedActions": [...]
    }
  ]
}
```

## 🧪 Testing Different Scenarios

### Low Risk Example
```
Citizenship: UZB (Uzbekistan)
MainAccount: retail_banking
ResidentStatus: RESIDENT
Expected Result: LOW (score 0-24)
```

### High Risk Example
```
Citizenship: IRN (Iran)
MainAccount: international_money_service_business
ResidentStatus: NON_RESIDENT
IsVPN: Y
Expected Result: HIGH/CRITICAL (score 75+)
```

## 🛠️ Development

### Project Structure

```
ai-service/app/
├── main.py                      # FastAPI endpoints
├── bulk_orchestrator.py         # Main orchestration
├── bulk_risk_engine.py          # Risk scoring (NEW: VPN, device, occupation)
├── bulk_excel_parser.py         # Excel parsing (NEW: optional columns)
├── bulk_sanctions_matcher.py    # Sanctions matching (NEW: birthdate logic)
├── agent_risk_explainer.py      # Azure OpenAI integration (FIXED)
├── agent_sanctions_decision.py  # Sanctions review
├── azure_openai_client.py       # OpenAI client
├── bulk_models.py              # Pydantic models
└── pure_risk_scorer.py         # Core risk rules
```

### Running Tests

```bash
# Run service in dev mode
docker compose up

# View logs
docker compose logs -f ai-service

# Restart after code changes
docker compose restart ai-service
```

## 🐛 Troubleshooting

### Pydantic Validation Errors (FIXED)
**Issue**: `Field required [type=missing]` errors  
**Solution**: Updated `agent_risk_explainer.py` with proper validation and fallback logic

### Azure OpenAI Connection Failed
**Issue**: Cannot connect to Azure OpenAI  
**Solution**: 
1. Verify `.env` file has correct credentials
2. Check Azure Portal that deployment exists
3. Ensure API key is valid

### Missing Required Columns
**Issue**: Excel validation fails  
**Solution**: See [EXCEL_TEMPLATE_SPEC.md](EXCEL_TEMPLATE_SPEC.md) for required columns

### Device Tracking Not Working
**Issue**: DEVICE_REUSE not detected  
**Solution**: Add `DeviceId` column to your Excel file

## 📦 Deployment

### Production Checklist

- [ ] Configure Azure OpenAI with production deployment
- [ ] Set up proper logging and monitoring
- [ ] Configure rate limits for Azure OpenAI
- [ ] Set up database for persistent storage (if needed)
- [ ] Review and customize risk rules for your region
- [ ] Update FATF lists with current data
- [ ] Test with production-like data volumes
- [ ] Set up backup and disaster recovery
- [ ] Review data privacy and compliance requirements
- [ ] Configure SSL/TLS for API endpoint

## 🤝 Contributing

This is a private compliance project. Contact the team for contribution guidelines.

## 📄 License

See LICENSE file for details.

## 🔗 Related Documentation

- [Implementation Guide](IMPLEMENTATION_GUIDE.md) - Full technical documentation
- [Quick Start](QUICKSTART.md) - 5-minute setup guide  
- [Excel Template](EXCEL_TEMPLATE_SPEC.md) - Input file specification
- [Example Response](example-response-body.json) - Sample output

## ⚠️ Important Notes

1. **Azure OpenAI Costs**: Each customer requires ~2 API calls. Monitor usage.
2. **Rate Limits**: Azure OpenAI has rate limits. Consider batching for large files.
3. **Data Privacy**: Customer data is sent to Azure OpenAI. Ensure compliance.
4. **Model Choice**: Use GPT-4 or GPT-4o (NOT GPT-3.5) for best results.
5. **Device Tracking**: Resets per batch upload (not persistent across sessions).
- `NationalityDesc`, `CitizenshipDesc` - Descriptive fields

#### Sample Data:

| CustomerNo | DocumentName | BirthCountry | Citizenship | Nationality | MainAccount | RiskFlag | LocalBlackListFlag |
|------------|--------------|--------------|-------------|-------------|-------------|----------|-------------------|
| CUST-001 | John Smith | United States | USA | American | accountant | | N |
| CUST-002 | Ali Reza | Iran | IRN | Iranian | money_service_business | | N |
| CUST-003 | Kim Jong | North Korea | PRK | North Korean | trader | | N |
| CUST-004 | Maria Garcia | Philippines | PHL | Filipino | nurse | PEP | N |
| CUST-005 | Ahmed Hassan | Syria | SYR | Syrian | restaurant_owner | | N |

### Test Using PowerShell

```powershell
# Test with curl (simple)
curl -X POST "http://localhost:8000/risk/batch-excel?use_llm=false" `
  -F "file=@test_customers.xlsx" `
  -o result_customers.xlsx

# The processed file will be saved as result_customers.xlsx
```

### Test Using Python Script

Create `test_batch.py`:

```python
import requests

# Test endpoint
url = "http://localhost:8000/risk/batch-excel"

# Open your Excel file
with open("test_customers.xlsx", "rb") as f:
    files = {"file": ("test_customers.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    params = {"use_llm": False}  # Set to True for LLM analysis (slower but more accurate)
    
    response = requests.post(url, files=files, params=params)
    
    if response.status_code == 200:
        # Save the result
        with open("result_customers.xlsx", "wb") as result:
            result.write(response.content)
        print("✅ Processing complete! Check result_customers.xlsx")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
```

Run:
```powershell
python test_batch.py
```

### Test Using Swagger UI

1. Open http://localhost:8000/docs in your browser
2. Find the `POST /risk/batch-excel` endpoint
3. Click "Try it out"
4. Upload your Excel file
5. Set `use_llm` parameter (True or False)
6. Click "Execute"
7. Download the response file

---

## 🔍 Understanding the Output

The processed Excel file will include three new columns:

### Added Columns:

1. **RiskScore** (0-100)
   - 0-49: Low risk (GREEN)
   - 50-79: Medium risk (YELLOW)
   - 80-100: High risk (RED)

2. **RiskFlag**
   - `GREEN` - Low risk, standard monitoring
   - `YELLOW` - Medium risk, enhanced monitoring
   - `RED` - High risk, requires immediate review

3. **RiskReason**
   - Semicolon-separated list of risk factors
   - Examples:
     - `FATF_BLACK_LIST_COUNTRY`
     - `SANCTIONS_MATCH_FUZZY`
     - `PEP_STATUS`
     - `HIGH_RISK_OCCUPATION`

### Risk Scoring Logic:

- **FATF Black List** (Iran, North Korea, Myanmar): +80 points
- **FATF Grey List** (Syria, Philippines, etc.): +40 points
- **UN/EU Sanctions Match**: +50 points
- **Local Blacklist**: +50 points
- **PEP Status**: +30 points
- **High-Risk Occupations**: +20-30 points
- **Country Mismatches**: +10-15 points

---

## 🎯 Other Available Endpoints

### 1. Mock Response Endpoint

Returns a predefined sample response (useful for testing):

```powershell
curl -X POST http://localhost:8000/mock-response -H "Content-Type: application/json" -d '{}'
```

### 2. Single Customer Risk Assessment

Assess risk for a customer stored in the database:

```powershell
curl -X POST http://localhost:8000/risk/from-db `
  -H "Content-Type: application/json" `
  -d '{"customer_no": "CUST-001", "use_llm": true}'
```

---

## 🛠️ Configuration

### LLM vs Pure Algorithm

The `use_llm` parameter controls the analysis method:

- **`use_llm=false`** (Recommended for testing)
  - Fast processing (~1-2 seconds per customer)
  - Pure algorithmic rules
  - Deterministic results
  - No external API calls

- **`use_llm=true`** (Production-ready but slower)
  - Slower processing (~5-10 seconds per customer)
  - Uses Ollama LLM for enhanced analysis
  - More nuanced risk assessment
  - Requires RAG embeddings and context

### Environment Variables

Edit `docker-compose.yml` to customize:

```yaml
environment:
  PGHOST: db
  PGPORT: "5432"
  PGDATABASE: "InternalControlDb"
  PGUSER: "postgres"
  PGPASSWORD: "admin"
  OLLAMA_URL: "http://ollama:11434"
  EMBED_MODEL: "nomic-embed-text"
  GEN_MODEL: "llama3:8b"
  LOG_DIR: "/var/log/ai-service"
```

---

## 📝 Logs

View service logs:

```powershell
# All services
docker-compose logs -f

# AI service only
docker-compose logs -f ai-service

# Last 100 lines
docker-compose logs --tail=100 ai-service

# Log files are also saved to ./logs/ directory
```

---

## 🔧 Troubleshooting

### Services won't start

```powershell
# Check Docker is running
docker version

# Remove old containers and rebuild
docker-compose down -v
docker-compose up -d --build
```

### Ollama models not found

```powershell
# Re-download models
docker exec -it compliance-ai-service-ollama-1 ollama pull nomic-embed-text
docker exec -it compliance-ai-service-ollama-1 ollama pull llama3:8b

# List installed models
docker exec -it compliance-ai-service-ollama-1 ollama list
```

### Excel processing fails

Check these common issues:
- Excel file must have required columns: `CustomerNo`, `DocumentName`, `BirthCountry`, `Citizenship`
- File must be .xlsx or .xls format
- Column names are case-sensitive
- File should not be corrupted or password-protected

### API returns 500 error

```powershell
# Check logs for details
docker-compose logs ai-service

# Restart the service
docker-compose restart ai-service
```

---

## 🛑 Stopping the Services

```powershell
# Stop services (keep data)
docker-compose down

# Stop and remove all data
docker-compose down -v
```

---

## 📚 API Documentation

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🏗️ Project Structure

```
compliance-ai-service/
├── ai-service/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── excel_processor.py         # Excel batch processing logic
│   │   ├── pure_risk_scorer.py        # Algorithm-based risk scoring
│   │   ├── llm_sanctions_risk.py      # LLM-enhanced risk assessment
│   │   ├── sanctions_loader.py        # Load UN/EU/FATF sanctions data
│   │   ├── sanction_matching.py       # Fuzzy name matching
│   │   ├── rag_engine.py              # RAG embeddings and generation
│   │   ├── storage.py                 # In-memory document store
│   │   ├── customer_mapper.py         # Map Excel rows to profiles
│   │   ├── ingest_sanctions.py        # Ingest sanctions into RAG
│   │   ├── logging_config.py          # Logging configuration
│   │   └── db.py                      # Database operations
│   ├── sunction-lists/
│   │   ├── fatf-countries.json        # FATF risk countries
│   │   └── UN-sunctions-list.html     # UN sanctions data
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── logs/                               # Application logs
└── README.md                           # This file
```

---

## 📄 License

See LICENSE file for details.
