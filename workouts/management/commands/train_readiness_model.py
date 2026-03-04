import os
import joblib
import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

class Command(BaseCommand):
    help = 'Train Readiness/Fatigue prediction ML model'

    def handle(self, *args, **options):
        np.random.seed(42)
        n_samples = 1500
        
        # 16 features: 
        # last_1_day_nelu, rolling_3_day_nelu, rolling_7_day_nelu, last_session_cns, days_since_last_rest, acute_load, chronic_load, acwr, avg_3_day_cals, cal_dev, avg_prot_per_kg, avg_hyd, age, weight, discipline_enc, bmi
        
        X = np.random.rand(n_samples, 16)
        X[:, 0] *= 250   # last 1 day
        X[:, 1] *= 600   # 3 day
        X[:, 2] *= 1200  # 7 day
        X[:, 3] = X[:, 3] * 5 + 5 # cns 5-10
        X[:, 4] *= 7     # days since rest
        X[:, 5] = X[:, 2] * 1.1 # acute load
        X[:, 6] = X[:, 6] * 1000 + 200 # chronic
        X[:, 7] = X[:, 5] / (X[:, 6] + 1) # acwr
        X[:, 8] = X[:, 8] * 2000 + 1500 # cals
        X[:, 9] = X[:, 8] - 3000 # cal dev
        X[:, 10] = X[:, 10] * 2.0 + 0.5 # protein per kg
        X[:, 11] = X[:, 11] * 4.0 + 1.0 # hydration
        X[:, 12] = X[:, 12] * 20 + 18 # age
        X[:, 13] = X[:, 13] * 40 + 60 # weight
        X[:, 14] = np.random.randint(0, 4, n_samples) # discipline
        X[:, 15] = X[:, 13] / ((1.8)**2) # bmi
        
        # Target: Fatigue 0-100
        # High loads = more fatigue, low recovery = more fatigue
        # Baseline ~ 40
        y = 40.0 + (X[:, 1] / 600.0) * 20 + (X[:, 7] > 1.3) * 15 - (X[:, 4] > 2) * 15 - (X[:, 10] > 1.6) * 10 - (X[:, 11] > 3.0) * 5
        y = np.clip(y + np.random.normal(0, 5, n_samples), 0, 100)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_scaled, y)
        
        output_dir = os.path.join(settings.BASE_DIR, 'ml_models')
        os.makedirs(output_dir, exist_ok=True)
        
        joblib.dump(model, os.path.join(output_dir, 'readiness_model.joblib'))
        joblib.dump(scaler, os.path.join(output_dir, 'readiness_scaler.joblib'))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully trained and saved Readiness Model to {output_dir}"))
