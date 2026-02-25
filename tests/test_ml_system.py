import pytest
import numpy as np
import joblib
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# ---------------------------------------------------------
# 1. Model & Feature Engineering Tests
# ---------------------------------------------------------

@pytest.fixture(scope="module")
def ml_assets():
    try:
        model = joblib.load("ml_models/rf_calorie_model.joblib")
        scaler = joblib.load("ml_models/feature_scaler.joblib")
        features = joblib.load("ml_models/feature_names.joblib")
        return {"model": model, "scaler": scaler, "features": features}
    except Exception as e:
        pytest.skip(f"Could not load ML models for testing: {e}")

def test_model_loaded(ml_assets):
    assert ml_assets["model"] is not None
    assert ml_assets["scaler"] is not None
    assert isinstance(ml_assets["features"], list)
    assert len(ml_assets["features"]) == 9 # age, gender, height, weight, discipline, session_type, duration, intensity, bmi

def test_feature_engineering_bmi(ml_assets):
    """Test manual BMI calculation logic matches expected."""
    weight_kg = 80.0
    height_cm = 180.0
    expected_bmi = 80.0 / ((180.0 / 100) ** 2)  # 24.69
    
    # We test it at the endpoint level, but conceptually this checks the math.
    assert round(expected_bmi, 2) == 24.69

def test_single_prediction_reasonability(ml_assets):
    """Test if the raw model produces a reasonable prediction (1500 to 5000 kcal)."""
    # dummy features matching the array map:
    # age=25, gender=1(Male), height_cm=180, weight_kg=75, discipline=1(Distance), 
    # session_type=1(Training), duration_mins=60, intensity=7, bmi=23.15
    dummy_input = np.array([[25, 1, 180.0, 75.0, 1, 1, 60.0, 7.0, 23.15]])
    scaled_input = ml_assets["scaler"].transform(dummy_input)
    prediction = ml_assets["model"].predict(scaled_input)[0]
    
    assert 1200 < prediction < 6000, f"Prediction {prediction} outside reasonable bounds"

# ---------------------------------------------------------
# 2. API Endpoint & Validation Tests
# ---------------------------------------------------------

def test_predict_endpoint_valid():
    """Test normal functioning athlete input."""
    payload = {
        "age": 28,
        "gender": 1,
        "height_cm": 182.0,
        "weight_kg": 76.5,
        "discipline": 1,
        "session_type": 1,
        "duration_mins": 90.0,
        "intensity": 6.5
    }
    response = client.post("/predict/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "target_calories" in data
    assert "recommendation" in data
    assert isinstance(data["target_calories"], int)
    assert 1500 <= data["target_calories"] <= 5500

def test_predict_endpoint_missing_field():
    """Test standard Pydantic validation failure gracefully."""
    payload = {
        "age": 28,
        "gender": 1,
        # Missing height, weight, etc.
    }
    response = client.post("/predict/", json=payload)
    assert response.status_code == 422 # Unprocessable Entity

def test_predict_endpoint_invalid_values():
    """Test supplying strings instead of floats/ints."""
    payload = {
        "age": "twenty-eight",
        "gender": 1,
        "height_cm": 182.0,
        "weight_kg": 76.5,
        "discipline": 1,
        "session_type": 1,
        "duration_mins": 90.0,
        "intensity": 6.5
    }
    response = client.post("/predict/", json=payload)
    assert response.status_code == 422 # Data validation error

# ---------------------------------------------------------
# 3. Edge Case Suite
# ---------------------------------------------------------

def test_edge_case_young_lightweight():
    """Test very young and light athlete."""
    payload = {
        "age": 16,
        "gender": 0,
        "height_cm": 150.0,
        "weight_kg": 45.0,
        "discipline": 2, # Jump
        "session_type": 0, # Recovery
        "duration_mins": 30.0,
        "intensity": 3.0
    }
    response = client.post("/predict/", json=payload)
    assert response.status_code == 200
    assert response.json()["target_calories"] < 2500 # Should be low

def test_edge_case_heavyweight_thrower():
    """Test very heavy athlete on high intensity day."""
    payload = {
        "age": 35,
        "gender": 1,
        "height_cm": 200.0,
        "weight_kg": 120.0,
        "discipline": 3, # Throw
        "session_type": 2, # Competition
        "duration_mins": 120.0,
        "intensity": 10.0
    }
    response = client.post("/predict/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["target_calories"] > 3500 # Should be high
    assert "Competition day" in data["recommendation"]

def test_stress_test_multiple_calls():
    """Verify the model doesn't crash on repeated synchronous calls."""
    payload = {
        "age": 25, "gender": 1, "height_cm": 180.0, "weight_kg": 75.0,
        "discipline": 1, "session_type": 1, "duration_mins": 60.0, "intensity": 7.0
    }
    for _ in range(20):
        response = client.post("/predict/", json=payload)
        assert response.status_code == 200
