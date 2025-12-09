from typing import Dict, Any, Tuple
from .pure_risk_scorer import PureRiskScorer


class BulkRiskEngine:
    def __init__(self) -> None:
        self._scorer = PureRiskScorer()

    def _score_country_fatf(self, row: Dict[str, Any]) -> Tuple[int, str]:
        # reuse _derive_country/_check_fatf_country via wrapper methods
        main_country = self._scorer._derive_country(row)  # type: ignore
        score, reason = self._scorer._check_fatf_country(main_country)  # type: ignore
        return score, reason

    def _score_birth_country(self, row: Dict[str, Any]) -> Tuple[int, str]:
        # simplified: treat as sanctions-related but lower weight
        birth_country = str(row.get("BirthCountry") or "")
        score, reason = self._scorer._check_fatf_country(birth_country)  # type: ignore
        if score == 0:
            return 0, ""
        return score // 2, f"Birth country: {reason}"

    def _score_pep(self, row: Dict[str, Any]) -> Tuple[int, str]:
        return self._scorer._check_pep_status(row)  # type: ignore

    def _score_profile(self, row: Dict[str, Any]) -> Tuple[int, str]:
        # use cash-intensive occupations as a proxy for high-risk profile
        return self._scorer._check_cash_intensive_occupation(row)  # type: ignore

    def _score_device_and_digital(self, risk_input: Dict[str, Any]) -> Tuple[int, int, str]:
        """
        Very simple heuristics for now:
        - foreign IP vs. declared country -> device
        - suspicious email domain -> digitalFootprint
        You can refine with real GeoIP / domain risk.
        """
        digital_score = 0
        device_score = 0
        reasons = []

        email = (risk_input.get("digital") or {}).get("email") or ""
        ip = (risk_input.get("digital") or {}).get("ipAddress") or ""
        citizenship = (risk_input.get("citizenship") or "").upper()

        # example: treat .ru / .ir / .kp emails as slightly riskier (just for demo)
        if email and any(email.lower().endswith(tld) for tld in [".ru", ".ir", ".kp"]):
            digital_score += 10
            reasons.append(f"Email domain {email.split('@')[-1]} considered higher risk")

        # placeholder: if IP address is non-empty and citizenship is FATF black list, bump device risk
        if ip and citizenship in self._scorer.BLACK_LIST_COUNTRIES:
            device_score += 15
            reasons.append("Foreign IP / jurisdiction mismatch (placeholder rule)")

        return digital_score, device_score, "; ".join(reasons)

    def assess(self, risk_input: Dict[str, Any]) -> Dict[str, Any]:
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

        # birth country risk
        s, r = self._score_birth_country(row)
        sanctions_score += s
        if r:
            reasons.append(r)

        # PEP
        s, r = self._score_pep(row)
        pep_score += s
        if r:
            reasons.append(r)

        # occupation / profile
        s, r = self._score_profile(row)
        profile_score += s
        if r:
            reasons.append(r)

        # digital / device (using Email + IPAddress)
        ds, devs, r = self._score_device_and_digital(risk_input)
        digital_score += ds
        device_score += devs
        if r:
            reasons.append(r)

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
