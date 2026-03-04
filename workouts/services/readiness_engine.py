import os
import joblib
import numpy as np
from datetime import timedelta
from django.utils import timezone
from workouts.models import TrainingSession
from meals.models import NutritionLog
from users.models import UserProfile
from workouts.services.rule_engine import get_discipline_scalar

def calculate_approx_nelu(session):
    scalar = get_discipline_scalar(session.discipline)
    raw_elu = 50.0 # baseline
    if hasattr(session, 'runnersession'):
        raw_elu = (session.runnersession.distance_m * session.runnersession.repetitions) / 10.0
    elif hasattr(session, 'jumpersession'):
        raw_elu = session.jumpersession.attempts * session.jumpersession.best_jump_m * 10.0
    elif hasattr(session, 'throwersession'):
        raw_elu = session.throwersession.attempts * session.throwersession.implement_weight_kg * 5.0
    return raw_elu * scalar

def extract_features(user):
    today = timezone.now().date()
    
    # 1. Profile
    try:
        profile = UserProfile.objects.get(user=user)
        age = 25 # mock if dob missing
        if hasattr(profile, 'date_of_birth') and profile.date_of_birth:
            age = (today - profile.date_of_birth).days / 365.25
        weight = float(profile.weight_kg) if profile.weight_kg else 80.0
        bmi = float(profile.bmi) if profile.bmi else 24.0
        sport = profile.sport if profile.sport else 'General'
    except Exception:
        age, weight, bmi, sport = 25, 80.0, 24.0, 'General'

    discipline_map = {'Runner': 1, 'Jumper': 2, 'Thrower': 3, 'General': 0}
    discipline_enc = discipline_map.get(sport.title(), 0)

    # 2. Training Logs
    sessions = TrainingSession.objects.filter(user=user, date__lte=today).order_by('-date')
    
    last_1_day_nelu = 0.0
    rolling_3_day_nelu = 0.0
    rolling_7_day_nelu = 0.0
    acute_load = 0.0
    chronic_load = 0.0
    days_since_last_rest = 0
    last_session_cns = 5.0 

    if sessions.exists():
        last_date = sessions.first().date
        days_since_last_rest = (today - last_date).days
        
        four_weeks_ago = today - timedelta(days=28)
        recent_sessions = [s for s in sessions if s.date >= four_weeks_ago]
        
        for s in recent_sessions:
            nelu = calculate_approx_nelu(s)
            days_diff = (today - s.date).days
            
            if days_diff <= 1:
                last_1_day_nelu += nelu
            if days_diff <= 3:
                rolling_3_day_nelu += nelu
            if days_diff <= 7:
                rolling_7_day_nelu += nelu
            if days_diff <= 7:
                acute_load += nelu
            
            chronic_load += nelu
        
        chronic_load = chronic_load / 4.0
        
        disc_lower = sessions.first().discipline.lower()
        if 'throw' in disc_lower: last_session_cns = 8.5
        elif 'jump' in disc_lower: last_session_cns = 8.0
        else: last_session_cns = 7.0

    acwr = 1.0
    if chronic_load > 0:
        acwr = acute_load / chronic_load
        
    # 3. Nutrition Logs
    nutritions = NutritionLog.objects.filter(user=user, date__gte=today - timedelta(days=3))
    rolling_3_day_cals = 0.0
    rolling_3_day_protein = 0.0
    rolling_3_day_hyd = 0.0
    
    for n in nutritions:
        cals = (n.carbohydrates_g * 4.0) + (n.protein_g * 4.0) + (n.fats_g * 9.0)
        prot = n.protein_g
        hyd = n.hydration_liters if n.hydration_liters else 0.0
        
        rolling_3_day_cals += cals
        rolling_3_day_protein += prot
        rolling_3_day_hyd += hyd
        
    avg_3_day_cals = rolling_3_day_cals / 3.0
    cal_dev = avg_3_day_cals - 3000 # target assumed 3000
    avg_prot_per_kg = (rolling_3_day_protein / 3.0) / weight if weight else 0
    avg_hyd = rolling_3_day_hyd / 3.0
    
    feature_vector = [
        last_1_day_nelu,
        rolling_3_day_nelu,
        rolling_7_day_nelu,
        last_session_cns,
        days_since_last_rest,
        acute_load,
        chronic_load,
        acwr,
        avg_3_day_cals,
        cal_dev,
        avg_prot_per_kg,
        avg_hyd,
        age,
        weight,
        discipline_enc,
        bmi
    ]
    
    return np.array(feature_vector).reshape(1, -1)

def predict_readiness(user):
    try:
        from django.conf import settings
        base_dir = settings.BASE_DIR
        model_path = os.path.join(base_dir, 'ml_models', 'readiness_model.joblib')
        scaler_path = os.path.join(base_dir, 'ml_models', 'readiness_scaler.joblib')
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return 50.0 # safe fallback
            
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        
        X = extract_features(user)
        X_scaled = scaler.transform(X)
        pred = model.predict(X_scaled)[0]
        
        return max(0.0, min(100.0, float(pred)))
    except Exception as e:
        print(f"Readiness Prediction Error: {e}")
        return 50.0
