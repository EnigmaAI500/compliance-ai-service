from typing import Dict, Any, Tuple, List
from .pure_risk_scorer import PureRiskScorer


class BulkRiskEngine:
    """
    Enhanced risk scoring engine that handles:
    - FATF country risk (blacklist + grey list)
    - PEP detection
    - High-risk occupations and business categories
    - VPN and IP mismatch detection
    - Device reuse patterns
    - Email domain risk
    - Sanctions risk preparation
    """
    
    def __init__(self) -> None:
        self._scorer = PureRiskScorer()
        self._device_usage: Dict[str, List[str]] = {}  # deviceId -> list of customerNos
        
        # High-risk occupation categories
        self.HIGH_RISK_OCCUPATIONS = {
            "front_company_trader": 40,
            "international_money_service_business": 40,
            "cash_intensive_business": 30,
            "casino": 35,
            "cryptocurrency": 30,
            "money_exchange": 35,
            "real_estate": 20,
            "precious_metals": 25,
            "art_dealer": 20,
        }
        
        # High-risk email domains
        self.HIGH_RISK_EMAIL_DOMAINS = [
            ".ru", ".ir", ".kp", ".sy",  # High-risk country TLDs
            "tempmail", "guerrillamail", "10minutemail", "throwaway"  # Disposable
        ]

    def _score_country_fatf(self, row: Dict[str, Any]) -> Tuple[int, str]:
        """Score based on FATF country risk"""
        main_country = self._scorer._derive_country(row)  # type: ignore
        score, reason = self._scorer._check_fatf_country(main_country)  # type: ignore
        return score, reason

    def _score_birth_country(self, row: Dict[str, Any]) -> Tuple[int, str]:
        """Score based on birth country risk (lower weight than citizenship)"""
        birth_country = str(row.get("BirthCountry") or "")
        score, reason = self._scorer._check_fatf_country(birth_country)  # type: ignore
        if score == 0:
            return 0, ""
        # Birth country risk is half the weight of citizenship risk
        return score // 2, f"Birth country: {reason}"

    def _score_pep(self, row: Dict[str, Any]) -> Tuple[int, str]:
        """Check PEP status"""
        return self._scorer._check_pep_status(row)  # type: ignore

    def _score_occupation(self, risk_input: Dict[str, Any]) -> Tuple[int, str]:
        """
        Score high-risk occupations and business categories
        """
        business = risk_input.get("business") or {}
        main_account = (business.get("mainAccount") or "").lower().strip()
        occupation = (business.get("occupation") or "").lower().strip()
        
        score = 0
        reasons = []
        
        # Check main account category
        for risk_category, risk_score in self.HIGH_RISK_OCCUPATIONS.items():
            if risk_category in main_account:
                score = max(score, risk_score)
                reasons.append(f"High-risk business category: {risk_category.replace('_', ' ')}")
                break
        
        # Check occupation field
        if occupation:
            for risk_category, risk_score in self.HIGH_RISK_OCCUPATIONS.items():
                if risk_category.replace("_", " ") in occupation:
                    score = max(score, risk_score)
                    if f"High-risk occupation: {occupation}" not in reasons:
                        reasons.append(f"High-risk occupation: {occupation}")
                    break
        
        # Fallback to original cash-intensive check if no match
        if score == 0:
            s, r = self._scorer._check_cash_intensive_occupation(risk_input.get("rawRow", {}))  # type: ignore
            if s > 0:
                score = s
                reasons.append(r)
        
        return score, "; ".join(reasons) if reasons else ""

    def _score_vpn_and_ip(self, risk_input: Dict[str, Any]) -> Tuple[int, str]:
        """
        Detect VPN usage and IP/country mismatches
        """
        digital = risk_input.get("digital") or {}
        citizenship = (risk_input.get("citizenship") or "").upper()
        resident_status = (risk_input.get("residency") or {}).get("residentStatus") or ""
        
        score = 0
        reasons = []
        
        # Check VPN usage
        is_vpn = digital.get("isVPN", False)
        if is_vpn:
            score += 10
            reasons.append("VPN usage detected")
        
        # Check IP country mismatch
        ip_country = (digital.get("ipCountry") or "").upper()
        if ip_country and citizenship and ip_country != citizenship:
            # Non-resident with foreign IP is expected, lower score
            if "NON" in resident_status.upper():
                score += 5
                reasons.append(f"IP country ({ip_country}) differs from citizenship ({citizenship}) - expected for non-resident")
            else:
                score += 15
                reasons.append(f"IP country ({ip_country}) mismatch with citizenship ({citizenship})")
        
        # Check if IP is from high-risk country
        if ip_country in self._scorer.BLACK_LIST_COUNTRIES:
            score += 20
            reasons.append(f"IP from FATF high-risk jurisdiction: {ip_country}")
        
        return score, "; ".join(reasons) if reasons else ""

    def _score_device_reuse(self, risk_input: Dict[str, Any]) -> Tuple[int, str]:
        """
        Detect device reuse across multiple customers
        """
        digital = risk_input.get("digital") or {}
        device_id = digital.get("deviceId") or ""
        customer_no = risk_input.get("customerNo") or ""
        
        if not device_id or not customer_no:
            return 0, ""
        
        # Track device usage
        if device_id not in self._device_usage:
            self._device_usage[device_id] = []
        
        if customer_no not in self._device_usage[device_id]:
            self._device_usage[device_id].append(customer_no)
        
        # Score based on reuse count
        reuse_count = len(self._device_usage[device_id])
        
        if reuse_count >= 5:
            return 20, f"Device reused by {reuse_count} customers"
        elif reuse_count >= 3:
            return 10, f"Device reused by {reuse_count} customers"
        
        return 0, ""

    def _score_email_risk(self, risk_input: Dict[str, Any]) -> Tuple[int, str]:
        """
        Detect high-risk email domains
        """
        digital = risk_input.get("digital") or {}
        email = (digital.get("email") or "").lower()
        
        if not email or "@" not in email:
            return 0, ""
        
        score = 0
        reasons = []
        
        email_domain = email.split("@")[-1]
        
        # Check against high-risk domains
        for risk_domain in self.HIGH_RISK_EMAIL_DOMAINS:
            if risk_domain in email_domain:
                score = 10
                reasons.append(f"High-risk email domain: {email_domain}")
                break
        
        return score, "; ".join(reasons) if reasons else ""

    def assess(self, risk_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main assessment method that calculates risk score and level
        Returns dict with score, riskLevel, breakdown, and drivers
        """
        row = dict(risk_input.get("rawRow") or {})

        # Local blacklist check – keep your existing "hard red" behaviour
        score_local, reason_local = self._scorer._check_local_blacklist(row)  # type: ignore
        if score_local > 0:
            breakdown = {
                "sanctions": 100,
                "pep": 0,
                "digitalFootprint": 0,
                "device": 0,
                "profile": 0,
            }
            return {
                "score": 100,
                "riskLevel": "CRITICAL",
                "breakdown": breakdown,
                "drivers": [reason_local],
            }

        sanctions_score = 0
        pep_score = 0
        profile_score = 0
        digital_score = 0
        device_score = 0
        reasons = []

        # FATF / country risk
        s, r = self._score_country_fatf(row)
        sanctions_score += s
        if r:
            reasons.append(r)

        # Birth country risk
        s, r = self._score_birth_country(row)
        sanctions_score += s
        if r:
            reasons.append(r)

        # PEP
        s, r = self._score_pep(row)
        pep_score += s
        if r:
            reasons.append(r)

        # Occupation / profile
        s, r = self._score_occupation(risk_input)
        profile_score += s
        if r:
            reasons.append(r)

        # VPN and IP mismatch
        s, r = self._score_vpn_and_ip(risk_input)
        digital_score += s
        if r:
            reasons.append(r)

        # Device reuse
        s, r = self._score_device_reuse(risk_input)
        device_score += s
        if r:
            reasons.append(r)

        # Email risk
        s, r = self._score_email_risk(risk_input)
        digital_score += s
        if r:
            reasons.append(r)

        # Calculate total score
        total = sanctions_score + pep_score + profile_score + digital_score + device_score
        total = max(0, min(100, total))

        # 4-band mapping
        if total >= 75:
            level = "CRITICAL"
        elif total >= 50:
            level = "HIGH"
        elif total >= 25:
            level = "MEDIUM"
        else:
            level = "LOW"

        breakdown = {
            "sanctions": sanctions_score,
            "pep": pep_score,
            "digitalFootprint": digital_score,
            "device": device_score,
            "profile": profile_score,
        }

        if not reasons:
            reasons = ["No high-risk factors detected"]

        return {
            "score": total,
            "riskLevel": level,
            "breakdown": breakdown,
            "drivers": reasons,
        }
    
    def reset_device_tracking(self):
        """Reset device tracking between batches"""
        self._device_usage.clear()
