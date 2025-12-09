# CHANGELOG

All notable changes to the Compliance AI Service project.

## [2.0.0] - 2025-12-09

### 🎯 Major Release - Azure OpenAI Integration & Enhanced Risk Detection

This release completely resolves the Pydantic validation errors and implements comprehensive risk assessment features.

### Fixed
- **Critical**: Resolved Pydantic validation errors in `/risk/bulk-excel` endpoint
  - Fixed missing `confidence`, `riskDrivers`, `breakdown` fields in risk object
  - Fixed incorrect data types for `tags[].evidence` (was string, now dict)
  - Fixed incorrect data types for `recommendedActions[]` (was string, now object)
  - Added validation and type conversion in `agent_risk_explainer.py`
  - Implemented fallback to deterministic responses if LLM fails

### Added
- **Azure OpenAI Integration**
  - Comprehensive prompt engineering for structured JSON output
  - Post-processing validation to ensure Pydantic compliance
  - Fallback to deterministic rules if Azure OpenAI unavailable
  - Environment-based configuration (.env file)

- **Enhanced Risk Detection**
  - VPN detection and scoring (+10 points)
  - IP country mismatch detection (+5-20 points)
  - Device reuse tracking across customers (+10-20 points)
  - Email domain risk analysis (+10 points)
  - Birth country risk assessment (half weight of citizenship)
  
- **High-Risk Occupation Detection**
  - Front company trader (+40 points, CRITICAL)
  - International money service business (+40 points, CRITICAL)
  - Casino operations (+35 points, CRITICAL)
  - Money exchange (+35 points, CRITICAL)
  - Cash-intensive business (+30 points, HIGH)
  - Cryptocurrency services (+30 points, HIGH)
  - Precious metals (+25 points, MEDIUM)
  - Real estate (+20 points, MEDIUM)
  - Art dealers (+20 points, MEDIUM)

- **Enhanced Sanctions Matching**
  - Improved name similarity algorithm
  - Token-based comparison for name variants
  - Confidence scoring with multiple factors
  - Infrastructure ready for birthdate and birthplace matching

- **Excel Parser Enhancements**
  - Support for optional columns: Email, IPAddress, IPCountry, IsVPN, DeviceId, Occupation, BirthDate
  - VPN flag conversion (Y/N/YES/TRUE to boolean)
  - Comprehensive validation with warnings for missing optional fields

- **Documentation**
  - QUICKSTART.md - 5-minute setup guide
  - IMPLEMENTATION_GUIDE.md - Comprehensive technical documentation
  - EXCEL_TEMPLATE_SPEC.md - Complete input file specification
  - IMPLEMENTATION_SUMMARY.md - Overview of changes
  - DEPLOYMENT_CHECKLIST.md - Production deployment guide
  - .env.example - Configuration template

### Changed
- **Risk Scoring Engine** (`bulk_risk_engine.py`)
  - Modular scoring methods for each risk factor
  - Device tracking with batch reset capability
  - Enhanced breakdown reporting (5 categories)
  - Maximum scores: Sanctions(50), PEP(30), Profile(40), Digital(30), Device(20)

- **Orchestrator** (`bulk_orchestrator.py`)
  - Device tracking reset per batch
  - Enhanced risk driver mapping (10 tag types)
  - Updated engine version to v2.0.0
  - Improved scoring model name: "weighted-rules+azure-openai"

- **README.md**
  - Complete overhaul with new feature descriptions
  - Risk scoring system documentation
  - Architecture diagram
  - Troubleshooting section
  - Production checklist

### Technical Details

**File Changes**:
- `ai-service/app/agent_risk_explainer.py` - Complete rewrite (280 lines)
- `ai-service/app/bulk_risk_engine.py` - Enhanced with 6 new methods (260 lines)
- `ai-service/app/bulk_sanctions_matcher.py` - Enhanced matching logic (160 lines)
- `ai-service/app/bulk_excel_parser.py` - Added 7 optional columns
- `ai-service/app/bulk_orchestrator.py` - Device tracking and improved summary

**New Files**:
- `.env.example` - Configuration template
- `QUICKSTART.md` - Quick setup guide
- `IMPLEMENTATION_GUIDE.md` - Technical documentation (500+ lines)
- `EXCEL_TEMPLATE_SPEC.md` - Input specification (200+ lines)
- `IMPLEMENTATION_SUMMARY.md` - Change summary
- `DEPLOYMENT_CHECKLIST.md` - Production checklist

**Dependencies**:
- No new dependencies required
- Existing `openai>=1.50.0` used for Azure OpenAI

### Migration Guide

**From v1.x to v2.0:**

1. **Set up Azure OpenAI**:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

2. **Update Excel files** (optional columns):
   - Add `Email` column for email domain risk
   - Add `IPAddress`, `IPCountry`, `IsVPN` for geo-risk
   - Add `DeviceId` for device reuse detection
   - Add `Occupation` for occupation-based risk
   - Add `BirthDate` (YYYY-MM-DD) for enhanced sanctions matching

3. **Rebuild containers**:
   ```bash
   docker compose down
   docker compose up --build
   ```

4. **Test endpoint**:
   ```bash
   curl -X POST "http://localhost:8000/risk/bulk-excel?upload_country=UZ" \
     -F "file=@test.xlsx"
   ```

### Breaking Changes
- None. All changes are backward compatible.
- Existing Excel files without optional columns will still work.
- Response format matches v1.x structure with additional fields.

### Performance
- Processing time: ~2-5 seconds per customer (Azure OpenAI dependent)
- Memory usage: 4GB RAM recommended
- Optimal batch size: 10-100 customers per file
- Azure OpenAI costs: ~2 API calls per customer

### Known Issues
- Device tracking resets per batch (not persistent across sessions)
- Sanctions birthdate/birthplace matching requires enhanced data source
- IP geolocation requires IPCountry to be provided in Excel (no automatic lookup)

### Future Enhancements
- [ ] Real-time IP geolocation with MaxMind integration
- [ ] Enhanced sanctions database with birthdate/birthplace
- [ ] Parallel customer processing for speed
- [ ] Custom ML model training on historical data
- [ ] PDF report generation
- [ ] Web dashboard UI
- [ ] Persistent device tracking across sessions

---

## [1.5.0] - 2025-12-07 (Previous Version)

### Features
- Basic bulk Excel processing
- FATF country risk detection
- PEP detection
- Cash-intensive occupation detection
- Sanctions name matching
- LLM-based risk explanation

### Issues
- Pydantic validation errors on response
- Limited risk factor detection
- No VPN/device/email risk detection

---

## Version Numbering

This project uses Semantic Versioning (SemVer):
- **Major** (X.0.0): Breaking changes
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes

Current Version: **2.0.0**
