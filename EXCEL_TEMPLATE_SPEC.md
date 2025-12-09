# Excel Template Specification

## Required Columns

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| CustomerNo | String | Unique customer identifier | "CUST-001" |
| DocumentName | String | Full name as in document | "John Smith" |
| MainAccount | String | Business/account category | "international_money_service_business" |
| District | String | District name | "Shaykhontohur" |
| Region | String | Region name | "Tashkent City" |
| Locality | String | City/locality | "Tashkent" |
| Street | String | Street address | "Navoi 10" |
| Pinfl | String | Personal ID number | "12345678901234" |
| ExpiryDate | String/Date | Document expiry | "2030-12-31" |
| Nationality | String | Nationality code | "UZB" |
| NationalityDesc | String | Nationality description | "Uzbek" |
| BirthCountry | String | Country of birth | "Uzbekistan" |
| PassportIssuerCode | String | Issuer code | "UZ-TAS-01" |
| PassportIssuerPlace | String | Issuer place | "Tashkent" |
| Citizenship | String | Citizenship code (ISO 3166) | "UZB" |
| CitizenshipDesc | String | Citizenship description | "Uzbekistani" |
| RegDocType | String | Document type | "PASSPORT" |
| RegDocNum | String | Document number | "AA1234567" |
| RegDocSerialNum | String | Serial number | "AA" |
| RegPinfl | String | Registration PINFL | "12345678901234" |
| Lang | String | Language code | "uz" |
| AddressCode | String | Address code | "100000" |
| ResidentStatus | String | Resident or non-resident | "RESIDENT" or "NON_RESIDENT" |

## Optional Columns (Enhanced Risk Detection)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| **Email** | String | Customer email address | "customer@example.com" |
| **IPAddress** | String | Last known IP address | "185.123.45.67" |
| **IPCountry** | String | IP country code (ISO 3166) | "UZ" |
| **IsVPN** | String | VPN detection flag | "Y" or "N" |
| **DeviceId** | String | Device identifier | "device-12345" |
| **Occupation** | String | Customer occupation | "Money Service Business" |
| **BirthDate** | String/Date | Date of birth (for sanctions matching) | "1980-05-15" |
| RiskFlag | String | Historical risk flag | "RED", "YELLOW", "GREEN" |
| RiskScore | Integer | Historical risk score | 75 |
| RiskReason | String | Historical risk reason | "High-risk jurisdiction" |

## High-Risk Business Categories

Use these values in the `MainAccount` field for proper risk detection:

| Category | Risk Level | Score Impact |
|----------|-----------|--------------|
| front_company_trader | CRITICAL | +40 |
| international_money_service_business | CRITICAL | +40 |
| casino | CRITICAL | +35 |
| money_exchange | CRITICAL | +35 |
| cash_intensive_business | HIGH | +30 |
| cryptocurrency | HIGH | +30 |
| precious_metals | MEDIUM | +25 |
| real_estate | MEDIUM | +20 |
| art_dealer | MEDIUM | +20 |

## Country Codes (ISO 3166-1 Alpha-3)

### FATF Blacklist Countries (High Risk)
- IRN - Iran
- PRK - North Korea (Democratic People's Republic of Korea)
- SYR - Syria

### FATF Grey List Countries (Enhanced Monitoring)
- Check FATF website for current list

### Example Values
- UZB - Uzbekistan
- RUS - Russia
- USA - United States
- GBR - United Kingdom
- CHN - China

## Sample Data Rows

### Low Risk Customer
```
CustomerNo: CUST-001
DocumentName: Ali Karimov
MainAccount: retail_banking
District: Chilanzar
Region: Tashkent City
Locality: Tashkent
Street: Amir Temur 25
Citizenship: UZB
BirthCountry: Uzbekistan
ResidentStatus: RESIDENT
Email: ali.karimov@gmail.com
IPAddress: 82.215.10.15
IPCountry: UZ
IsVPN: N
```

### High Risk Customer
```
CustomerNo: CUST-002
DocumentName: REZA ALI
MainAccount: international_money_service_business
District: Shaykhontohur
Region: Tashkent City
Locality: Tashkent
Street: Navoi 10
Citizenship: IRN
BirthCountry: Iran
ResidentStatus: NON_RESIDENT
Email: reza@mail.ru
IPAddress: 5.62.123.45
IPCountry: RU
IsVPN: Y
DeviceId: device-99999
```

### Critical Risk Customer
```
CustomerNo: CUST-003
DocumentName: KIM CHOL
MainAccount: front_company_trader
District: Yashnobod
Region: Tashkent City
Locality: Tashkent
Street: Shota Rustaveli 15
Citizenship: PRK
BirthCountry: Democratic People's Republic of Korea
ResidentStatus: NON_RESIDENT
Email: kim@tempmail.com
IPAddress: 175.45.178.90
IPCountry: CN
IsVPN: Y
DeviceId: device-99999
```

## File Format Requirements

- **File Type**: Excel (.xlsx) or (.xls)
- **Sheet Name**: Must contain "Customers" sheet (or be the active sheet)
- **Header Row**: Must be within first 5 rows
- **Data Rows**: Start after header row
- **Empty Rows**: Will be skipped
- **File Size**: Recommended < 10 MB for optimal performance

## Validation Rules

The system performs automatic validation:

### Errors (Blocking)
- Missing required columns
- Empty file
- Invalid file format
- No data rows

### Warnings (Non-blocking)
- Missing optional columns
- Suspicious business categories
- Empty optional fields

## Excel Template Download

Create an Excel file with these column headers in the first row, then add your customer data starting from row 2.

**Tip**: You can copy the required columns from the table above and paste into Excel as the header row.
