"""
Debug test to see what's happening with the risk scorer.
"""
from app.pure_risk_scorer import PureRiskScorer


def debug_test():
    """Debug test with sample data matching Excel."""
    scorer = PureRiskScorer()
    
    # Test Iran customer (matches Excel data)
    test_iran = {
        "CustomerNo": "CUST-HR-100",
        "DocumentName": "ALI REZA (a.k.a. REZA ALI)",
        "BirthCountry": "Iran",
        "Citizenship": "IRN",
        "CitizenshipDesc": "Iran",
        "RiskFlag": "",
        "LocalBlackListFlag": "N"
    }
    
    print("Test Iran customer:")
    print(f"  Input data: {test_iran}")
    print()
    
    result = scorer.assess_risk(test_iran)
    print(f"  Result: {result}")
    print()
    
    # Let's trace through the logic manually
    print("Tracing logic:")
    print(f"  1. Main country = {scorer._derive_country(test_iran)}")
    print(f"  2. Birth country = {scorer._normalize(test_iran.get('BirthCountry', ''))}")
    print(f"  3. Black list countries = {scorer.BLACK_LIST_COUNTRIES}")
    print(f"  4. Is main country in black list? {scorer._normalize(scorer._derive_country(test_iran)) in scorer.BLACK_LIST_COUNTRIES}")
    
    # Test DPRK customer
    test_dprk = {
        "CustomerNo": "CUST-HR-090",
        "DocumentName": "KIM CHOL",
        "BirthCountry": "Democratic People's Republic of Korea",
        "Citizenship": "PRK",
        "CitizenshipDesc": "DPRK",
        "RiskFlag": "",
        "LocalBlackListFlag": "N"
    }
    
    print("\n\nTest DPRK customer:")
    print(f"  Input data: {test_dprk}")
    print()
    
    result = scorer.assess_risk(test_dprk)
    print(f"  Result: {result}")
    print()
    
    print("Tracing logic:")
    print(f"  1. Main country = {scorer._derive_country(test_dprk)}")
    print(f"  2. Normalized main country = {scorer._normalize(scorer._derive_country(test_dprk))}")
    print(f"  3. Is main country in black list? {scorer._normalize(scorer._derive_country(test_dprk)) in scorer.BLACK_LIST_COUNTRIES}")


if __name__ == "__main__":
    debug_test()
