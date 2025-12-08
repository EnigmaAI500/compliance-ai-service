# Compliance AI Service

AML/CFT Risk Assessment Service with sanctions matching, FATF country risk analysis, and LLM-powered compliance checks.

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- At least 8GB RAM available
- PowerShell or Command Prompt

### Step 1: Start the Services

```powershell
# Navigate to project directory
cd c:\Users\FirdavsMuzaffarov\Desktop\agent-projects\compliance-ai-service

# Start all services (PostgreSQL, Ollama, AI Service)
docker-compose up -d --build
```

This will start:
- **PostgreSQL** database on internal Docker network
- **Ollama** LLM service on port 11434
- **AI Service** FastAPI application on port 8000

### Step 2: Download Ollama Models

The AI service needs embedding and generation models:

```powershell
# Download embedding model (required for RAG)
docker exec -it compliance-ai-service-ollama-1 ollama pull nomic-embed-text

# Download generation model (for LLM analysis)
docker exec -it compliance-ai-service-ollama-1 ollama pull llama3:8b
```

**Note:** These models are large (embedding ~274MB, llama3 ~4.7GB). Download time depends on your internet speed.

### Step 3: Verify Services are Running

```powershell
# Check service status
docker-compose ps

# Check AI service logs
docker-compose logs ai-service

# Check if API is responding
curl http://localhost:8000/docs
```

You should see the FastAPI Swagger documentation at http://localhost:8000/docs

---

## 📊 Testing the Excel Batch Endpoint

### Create a Test Excel File

Create a file named `test_customers.xlsx` with these columns:

#### Required Columns:
- `CustomerNo` - Unique customer identifier
- `DocumentName` - Customer full name
- `BirthCountry` - Country of birth
- `Citizenship` - Citizenship code (ISO or full name)

#### Optional Columns (for better risk analysis):
- `Nationality` - Nationality description
- `MainAccount` - Occupation/account type
- `RiskFlag` - Set to "PEP" for Politically Exposed Persons
- `LocalBlackListFlag` - Set to "Y" if on local blacklist
- `ResidentStatus` - Resident status
- `District`, `Region`, `Locality`, `Street` - Address information
- `Pinfl` - Personal identification number
- `PassportIssuerCode`, `PassportIssuerPlace` - Passport details
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
