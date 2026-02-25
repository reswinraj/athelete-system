from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import joblib
import numpy as np

router = APIRouter(
    prefix="/predict",
    tags=["predictions"]
)

# Load model and scaler at startup
try:
    model = joblib.load("ml_models/rf_calorie_model.joblib")
    scaler = joblib.load("ml_models/feature_scaler.joblib")
    feature_names = joblib.load("ml_models/feature_names.joblib")
    print("Successfully loaded ML models.")
except Exception as e:
    print(f"Warning: Could not load ML models. {e}")
    model, scaler, feature_names = None, None, None

class PredictionRequest(BaseModel):
    age: int
    gender: int  # 0: Female, 1: Male
    height_cm: float
    weight_kg: float
    discipline: int  # 0: Sprint, 1: Distance, 2: Jump, 3: Throw
    session_type: int  # 0: Recovery, 1: Training, 2: Competition
    duration_mins: float
    intensity: float  # 1-10

class PredictionResponse(BaseModel):
    target_calories: int
    recommendation: str

@router.post("/", response_model=PredictionResponse)
async def predict_calories(request: PredictionRequest):
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="ML Model is currently unavailable.")
    
    try:
        # Create feature array matching the training data structure
        features = {
            'age': request.age,
            'gender': request.gender,
            'height_cm': request.height_cm,
            'weight_kg': request.weight_kg,
            'discipline': request.discipline,
            'session_type': request.session_type,
            'duration_mins': request.duration_mins,
            'intensity': request.intensity
        }
        
        # Calculate BMI (required feature)
        bmi = request.weight_kg / ((request.height_cm / 100) ** 2)
        features['bmi'] = bmi
        
        # Ensure correct order
        input_data = np.array([[features[name] for name in feature_names]])
        
        # Scale
        scaled_input = scaler.transform(input_data)
        
        # Predict
        prediction = model.predict(scaled_input)[0]
        target_calories = int(round(prediction))
        
        # Simple rule-based recommendation alongside the ML output
        rec = "Consume a balanced diet to meet your daily needs."
        if request.session_type == 2:
            rec = "Competition day: focus on high-carb pre-event meals and rapid post-event recovery."
        elif request.intensity >= 8:
            rec = "High intensity detected: ensure adequate protein intake (1.6-2.0g/kg) to repair muscle damage."
        elif target_calories > 3500:
            rec = "High calorie expenditure: consider liquid carbs during your session to maintain energy."

        return PredictionResponse(
            target_calories=target_calories,
            recommendation=rec
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
