import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure models directory exists
os.makedirs("ml_models", exist_ok=True)

def generate_smart_synthetic_data(n_samples=2500, random_state=42):
    """
    Generates a semi-realistic dataset for an athlete demo ML system.
    Predicts 'Target Calories' based on athlete stats and training load.
    """
    np.random.seed(random_state)
    
    # 1. Base Athlete Stats
    ages = np.random.randint(16, 45, n_samples)
    genders = np.random.choice([0, 1], n_samples)  # 0: Female, 1: Male
    
    # Realistic Height and Weight distributions based on gender
    heights_cm = np.where(genders == 1, 
                          np.random.normal(178, 8, n_samples), 
                          np.random.normal(164, 7, n_samples))
    weights_kg = np.where(genders == 1, 
                          np.random.normal(78, 10, n_samples), 
                          np.random.normal(62, 8, n_samples))
    
    # Clip extreme values
    heights_cm = np.clip(heights_cm, 150, 210)
    weights_kg = np.clip(weights_kg, 45, 120)
    
    # 2. Training Session Features
    # Disciplines: 0=Sprint, 1=Distance, 2=Jump, 3=Throw
    disciplines = np.random.choice([0, 1, 2, 3], n_samples, p=[0.3, 0.4, 0.15, 0.15])
    
    # Session Type: 0=Recovery, 1=Training, 2=Competition
    session_types = np.random.choice([0, 1, 2], n_samples, p=[0.2, 0.7, 0.1])
    
    # Duration (minutes) strongly correlated with discipline and session type
    base_durations = np.random.normal(60, 15, n_samples)
    durations = base_durations.copy()
    durations[disciplines == 1] += 30 # Distance runners train longer
    durations[session_types == 0] -= 20 # Recovery is shorter
    durations = np.clip(durations, 20, 180)
    
    # Intensity (1-10)
    intensities = np.random.normal(7, 1.5, n_samples)
    intensities[session_types == 0] = np.random.normal(4, 1, sum(session_types == 0))
    intensities[session_types == 2] = np.random.normal(9.5, 0.5, sum(session_types == 2))
    intensities = np.clip(np.round(intensities), 1, 10)
    
    # 3. Formulate DataFrame
    df = pd.DataFrame({
        'age': ages,
        'gender': genders,
        'height_cm': heights_cm,
        'weight_kg': weights_kg,
        'discipline': disciplines,
        'session_type': session_types,
        'duration_mins': durations,
        'intensity': intensities
    })
    
    # Feature Engineering
    df['bmi'] = df['weight_kg'] / ((df['height_cm'] / 100) ** 2)
    
    # 4. Generate Target (Target Calories for the day)
    # BMR calculation (Mifflin-St Jeor)
    bmr = np.where(df['gender'] == 1,
                   (10 * df['weight_kg']) + (6.25 * df['height_cm']) - (5 * df['age']) + 5,
                   (10 * df['weight_kg']) + (6.25 * df['height_cm']) - (5 * df['age']) - 161)
    
    # Activity multiplier based on session duration & intensity
    activity_burn = (df['duration_mins'] * df['intensity'] * (df['weight_kg'] / 70)) * 1.5
    
    # Target Calories with some natural noise
    df['target_calories'] = bmr + activity_burn + np.random.normal(0, 150, n_samples)
    df['target_calories'] = np.clip(np.round(df['target_calories']), 1200, 6000)
    
    return df

def train_and_save_model():
    print("Generating smart synthetic dataset...")
    df = generate_smart_synthetic_data()
    
    # Features & Target
    X = df.drop(columns=['target_calories'])
    y = df['target_calories']
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale numerical features (important for real-world robustness, though RF is scale-invariant, good practice)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("Training RandomForestRegressor...")
    # Simple but sensible hyperparameters (prevents overfitting to noise)
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    predictions = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    
    print(f"Model Training Complete!")
    print(f"MAE: {mae:.2f} kcal")
    print(f"R2 Score: {r2:.3f}")
    print(f"Feature Importances:")
    for name, imp in zip(X.columns, model.feature_importances_):
        print(f"  - {name}: {imp:.3f}")
        
    # Persist Model & Scaler
    joblib.dump(model, "ml_models/rf_calorie_model.joblib")
    joblib.dump(scaler, "ml_models/feature_scaler.joblib")
    # Save feature names for input validation
    joblib.dump(list(X.columns), "ml_models/feature_names.joblib")
    
    print("\nModels successfully saved to 'ml_models/' directory.")

if __name__ == "__main__":
    train_and_save_model()
