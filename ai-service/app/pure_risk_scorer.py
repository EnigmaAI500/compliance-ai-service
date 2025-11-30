"""
Pure algorithm-based risk scoring without LLM.
Simple, deterministic rules based on FATF lists, sanctions, and customer data.
"""
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta


class PureRiskScorer:
    """
    Pure algorithm-based risk assessment.
    No LLM, no external API calls - just deterministic rules.
    """
    
    def __init__(self):
        """Initialize with FATF country lists."""
        # FATF Black List - High Risk (North Korea, Iran, Myanmar)
        # Include common variations and ISO codes
        self.BLACK_LIST_COUNTRIES = {
            # Iran variations
            "IRAN", "IRN", "ISLAMIC REPUBLIC OF IRAN", "IR",
            # North Korea variations
            "NORTH KOREA", "DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA", "DPRK", 
            "KOREA NORTH", "PRK", "KP",
            # Myanmar variations
            "MYANMAR", "BURMA", "MMR", "MM"
        }
        
        # FATF Grey List - Increased Monitoring
        # Include common variations and ISO codes
        self.GREY_LIST_COUNTRIES = {
            # Countries
            "ALGERIA", "DZA", "ANGOLA", "AGO", "BOLIVIA", "BOL", 
            "BULGARIA", "BGR", "BURKINA FASO", "BFA",
            "CAMEROON", "CMR", "CROATIA", "HRV", "CRO",
            "DEMOCRATIC REPUBLIC OF CONGO", "DRC", "COD",
            "HAITI", "HTI", "JAMAICA", "JAM", "KENYA", "KEN", 
            "MALI", "MLI", "MOZAMBIQUE", "MOZ",
            "NAMIBIA", "NAM", "NIGERIA", "NGA", "PHILIPPINES", "PHL", "PH",
            "SENEGAL", "SEN", "SOUTH AFRICA", "ZAF", "ZA",
            "SOUTH SUDAN", "SSD", "SS",
            # Syria variations
            "SYRIA", "SYR", "SY", "SYRIAN ARAB REPUBLIC",
            # Turkey variations
            "TURKEY", "TUR", "TR", "TÜRKIYE", "TURKIYE",
            # Other countries
            "UGANDA", "UGA", "UNITED ARAB EMIRATES", "UAE", "ARE",
            "VENEZUELA", "VEN", "VIETNAM", "VNM", "VN",
            "YEMEN", "YEM", "ZIMBABWE", "ZWE",
            "CÔTE D'IVOIRE", "COTE D'IVOIRE", "COTE DIVOIRE", "IVORY COAST", "CIV"
        }
        
        # Cash-intensive occupations
        self.CASH_INTENSIVE_OCCUPATIONS = {
            "CURRENCY_EXCHANGE", "CURRENCY EXCHANGE", "MONEY EXCHANGE",
            "CASINO", "GAMBLING", "GAMING",
            "MONEY_TRANSFER", "MONEY TRANSFER", "REMITTANCE",
            "PAWN_SHOP", "PAWN SHOP", "PAWNBROKER",
            "JEWELRY", "JEWELLER", "JEWELER",
            "CAR DEALER", "AUTO DEALER", "VEHICLE SALES"
        }
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        return str(text).upper().strip()
    
    def _derive_country(self, row_data: Dict[str, Any]) -> str:
        """
        Derive primary country for risk assessment.
        Priority: CitizenshipDesc > Citizenship > Nationality > BirthCountry
        """
        candidates = [
            row_data.get("CitizenshipDesc"),
            row_data.get("Citizenship"),
            row_data.get("Nationality"),
            row_data.get("BirthCountry")
        ]
        
        for candidate in candidates:
            if candidate and str(candidate).strip():
                return self._normalize(candidate)
        
        return ""
    
    def _check_fatf_country(self, country: str) -> Tuple[int, str]:
        """
        Check if country is on FATF lists.
        Returns: (risk_score, reason)
        """
        normalized = self._normalize(country)
        
        if not normalized:
            return (0, "")
        
        # Check black list
        if normalized in self.BLACK_LIST_COUNTRIES:
            return (80, f"Country '{country}' is on FATF black list (high-risk jurisdiction)")
        
        # Check grey list
        if normalized in self.GREY_LIST_COUNTRIES:
            return (50, f"Country '{country}' is on FATF grey list (increased monitoring)")
        
        return (0, "")
    
    def _check_pep_status(self, row_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Check if customer is a Politically Exposed Person.
        Returns: (risk_score, reason)
        """
        risk_flag = self._normalize(str(row_data.get("RiskFlag", "")))
        
        if risk_flag == "PEP":
            return (30, "Customer is a Politically Exposed Person (PEP)")
        
        return (0, "")
    
    def _check_local_blacklist(self, row_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Check if customer is on local blacklist.
        Returns: (risk_score, reason)
        """
        blacklist_flag = self._normalize(str(row_data.get("LocalBlackListFlag", "")))
        
        if blacklist_flag == "Y" or blacklist_flag == "YES":
            return (100, "Customer is on local blacklist")
        
        return (0, "")
    
    def _check_cash_intensive_occupation(self, row_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Check if occupation is cash-intensive.
        Returns: (risk_score, reason)
        """
        occupation = self._normalize(str(row_data.get("MainAccount", "")))
        
        if not occupation:
            return (0, "")
        
        if occupation in self.CASH_INTENSIVE_OCCUPATIONS:
            return (15, f"Cash-intensive occupation: {occupation}")
        
        return (0, "")
    
    def _check_document_expiry(self, row_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Check document expiry date.
        Returns: (risk_score, reason)
        """
        expiry_date_str = str(row_data.get("ExpiryDate", "")).strip()
        
        if not expiry_date_str or expiry_date_str == "None":
            return (0, "")
        
        try:
            # Try parsing common date formats
            expiry_date = None
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not expiry_date:
                return (0, "")
            
            today = datetime.now()
            
            # Document expired
            if expiry_date < today:
                days_expired = (today - expiry_date).days
                return (20, f"Identity document expired {days_expired} days ago")
            
            # Document expiring soon (within 90 days)
            elif expiry_date <= today + timedelta(days=90):
                days_remaining = (expiry_date - today).days
                return (10, f"Identity document expires in {days_remaining} days")
            
        except Exception:
            pass
        
        return (0, "")
    
    def _check_resident_status(self, row_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Check resident status.
        Returns: (risk_score, reason)
        """
        status = self._normalize(str(row_data.get("ResidentStatus", "")))
        
        if status in ["NONRESIDENT", "NON-RESIDENT", "NON RESIDENT", "N"]:
            return (15, "Customer is non-resident")
        
        return (0, "")
    
    def _check_country_mismatch(self, row_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Check if birth country differs from current citizenship.
        Returns: (risk_score, reason)
        """
        birth_country = self._normalize(str(row_data.get("BirthCountry", "")))
        main_country = self._derive_country(row_data)
        
        if birth_country and main_country and birth_country != main_country:
            return (5, f"Birth country ({birth_country}) differs from citizenship ({main_country})")
        
        return (0, "")
    
    def assess_risk(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main risk assessment function using pure algorithm.
        
        Args:
            row_data: Dictionary with customer data from Excel row
            
        Returns:
            Dict with:
                - risk_score: int (0-100)
                - risk_flag: str (GREEN/YELLOW/RED)
                - risk_reason: str (semicolon-separated reasons)
        """
        total_score = 0
        reasons = []
        
        # 1. Local blacklist (immediate red flag)
        score, reason = self._check_local_blacklist(row_data)
        if score > 0:
            return {
                "risk_score": 100,
                "risk_flag": "RED",
                "risk_reason": reason
            }
        
        # 2. FATF country risk
        main_country = self._derive_country(row_data)
        score, reason = self._check_fatf_country(main_country)
        if score > 0:
            total_score += score
            reasons.append(reason)
        
        # 3. Birth country risk (if different from main country)
        birth_country = self._normalize(str(row_data.get("BirthCountry", "")))
        birth_country_different = birth_country and birth_country != main_country
        
        if birth_country_different:
            score, reason = self._check_fatf_country(birth_country)
            if score > 0:
                # Reduce weight for birth country vs current country
                total_score += (score // 2)
                reasons.append(f"Birth country: {reason}")
            else:
                # Birth country not on FATF lists, but still add small penalty for mismatch
                total_score += 5
                reasons.append(f"Birth country ({birth_country}) differs from citizenship ({main_country})")
        
        # 4. PEP status
        score, reason = self._check_pep_status(row_data)
        if score > 0:
            total_score += score
            reasons.append(reason)
        
        # 5. Cash-intensive occupation
        score, reason = self._check_cash_intensive_occupation(row_data)
        if score > 0:
            total_score += score
            reasons.append(reason)
        
        # 6. Document expiry
        score, reason = self._check_document_expiry(row_data)
        if score > 0:
            total_score += score
            reasons.append(reason)
        
        # 7. Resident status
        score, reason = self._check_resident_status(row_data)
        if score > 0:
            total_score += score
            reasons.append(reason)
        
        # Clamp score to 0-100
        total_score = max(0, min(100, total_score))
        
        # Determine risk flag
        if total_score >= 80:
            risk_flag = "RED"
        elif total_score >= 40:
            risk_flag = "YELLOW"
        else:
            risk_flag = "GREEN"
        
        # Build reason string
        if not reasons:
            risk_reason = "No high-risk factors detected"
        else:
            risk_reason = "; ".join(reasons)
        
        return {
            "risk_score": total_score,
            "risk_flag": risk_flag,
            "risk_reason": risk_reason
        }
