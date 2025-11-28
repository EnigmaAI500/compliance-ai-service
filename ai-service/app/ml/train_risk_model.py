import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

# 1) create synthetic data (for hackathon)
X = []
y = []

# Example: [country_risk_score, age, pep, cash_job]
# You can tune this later or generate from CSV.

def add_sample(country_risk, age, pep, cash_job, label):
    X.append([country_risk, age, int(pep), int(cash_job)])
    y.append(label)

# Some fake patterns
add_sample(90, 35, True, True, 1)
add_sample(90, 45, False, True, 1)
add_sample(20, 30, False, False, 0)
add_sample(50, 19, False, True, 1)
add_sample(10, 40, False, False, 0)
add_sample(60, 70, True, False, 1)
# Add more examples for balance...

X = np.array(X)
y = np.array(y)

model = LogisticRegression()
model.fit(X, y)

joblib.dump(model, "risk_model.pkl")
print("Model saved to risk_model.pkl")
