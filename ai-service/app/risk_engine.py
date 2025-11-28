import joblib
import numpy as np

class RiskMLModel:
    def __init__(self, model_path: str):
        self.model = joblib.load(model_path)

    def predict_proba(self, country_risk_score: int, age: int, pep: bool, cash_job: bool) -> float:
        x = np.array([[country_risk_score, age, int(pep), int(cash_job)]])
        proba = self.model.predict_proba(x)[0][1]  # probability of class 1 (suspicious)
        return float(proba)
