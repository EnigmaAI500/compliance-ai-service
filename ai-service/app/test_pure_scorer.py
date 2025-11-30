"""
Quick test of the pure risk scorer to verify it works correctly.
"""
from pure_risk_scorer import PureRiskScorer


def test_scorer():
    """Test the pure risk scorer with sample data."""
    scorer = PureRiskScorer()
    
    # Test 1: High risk - Iran (FATF black list)
    test1 = {
        "CustomerNo": "12345",
        "DocumentName": "John Doe",
        "BirthCountry": "Iran",
        "Citizenship": "Iran",
        "CitizenshipDesc": "Islamic Republic of Iran",
        "RiskFlag": "",
        "LocalBlackListFlag": "N"
    }
    result1 = scorer.assess_risk(test1)
    print("Test 1 - Iran citizen:")
    print(f"  Score: {result1['risk_score']}")
    print(f"  Flag: {result1['risk_flag']}")
    print(f"  Reason: {result1['risk_reason']}")
    print()
    
    # Test 2: Medium risk - Philippines (FATF grey list)
    test2 = {
        "CustomerNo": "12346",
        "DocumentName": "Jane Smith",
        "BirthCountry": "Philippines",
        "Citizenship": "Philippines",
        "CitizenshipDesc": "Philippines",
        "RiskFlag": "",
        "LocalBlackListFlag": "N"
    }
    result2 = scorer.assess_risk(test2)
    print("Test 2 - Philippines citizen:")
    print(f"  Score: {result2['risk_score']}")
    print(f"  Flag: {result2['risk_flag']}")
    print(f"  Reason: {result2['risk_reason']}")
    print()
    
    # Test 3: Low risk - USA (not on FATF lists)
    test3 = {
        "CustomerNo": "12347",
        "DocumentName": "Bob Johnson",
        "BirthCountry": "United States",
        "Citizenship": "USA",
        "CitizenshipDesc": "United States of America",
        "RiskFlag": "",
        "LocalBlackListFlag": "N"
    }
    result3 = scorer.assess_risk(test3)
    print("Test 3 - USA citizen:")
    print(f"  Score: {result3['risk_score']}")
    print(f"  Flag: {result3['risk_flag']}")
    print(f"  Reason: {result3['risk_reason']}")
    print()
    
    # Test 4: PEP + Grey list
    test4 = {
        "CustomerNo": "12348",
        "DocumentName": "Ahmed Hassan",
        "BirthCountry": "Syria",
        "Citizenship": "Syria",
        "CitizenshipDesc": "Syrian Arab Republic",
        "RiskFlag": "PEP",
        "LocalBlackListFlag": "N"
    }
    result4 = scorer.assess_risk(test4)
    print("Test 4 - Syrian PEP:")
    print(f"  Score: {result4['risk_score']}")
    print(f"  Flag: {result4['risk_flag']}")
    print(f"  Reason: {result4['risk_reason']}")
    print()
    
    # Test 5: Local blacklist (should be 100)
    test5 = {
        "CustomerNo": "12349",
        "DocumentName": "Criminal Person",
        "BirthCountry": "USA",
        "Citizenship": "USA",
        "RiskFlag": "",
        "LocalBlackListFlag": "Y"
    }
    result5 = scorer.assess_risk(test5)
    print("Test 5 - Local blacklist:")
    print(f"  Score: {result5['risk_score']}")
    print(f"  Flag: {result5['risk_flag']}")
    print(f"  Reason: {result5['risk_reason']}")
    print()


if __name__ == "__main__":
    test_scorer()
