import os
import sys
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'athlete_ai_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from workouts.models import TrainingSession, ThrowerSession
from meals.models import NutritionLog

def seed_rahul_data():
    # 1. User Credentials
    username = 'rahulkumar'
    password = 'demopassword123!'
    email = 'rahul@gmail.com'

    # Clean existing
    User.objects.filter(username=username).delete()

    user = User.objects.create_user(username=username, password=password, email=email)
    user.first_name = 'Rahul'
    user.last_name = 'Kumar'
    user.save()

    print(f"Created User: {username} | Password: {password}")

    # 2. User Profile (Thrower, 26yo, Power Athlete)
    # 26 years old from today
    dob = date.today().replace(year=date.today().year - 26)
    
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.date_of_birth = dob
    profile.gender = 'Male'
    profile.height_cm = 188.0
    profile.weight_kg = 112.5 # Heavy power build (BMI ~31.8)
    profile.sport = 'Shot Put'
    profile.role = 'Athlete'
    profile.save()

    print(f"Created Profile: {profile.weight_kg}kg, {profile.height_cm}cm, DOB: {profile.date_of_birth}")

    # 3. Training Logs (20 sessions over standard progression)
    # We will lay out a 4-week block (28 days ago to today) with 5 sessions per week
    start_date = date.today() - timedelta(days=28)
    
    # Progression base metrics
    base_throw = 15.5 # meters
    base_weight = 7.26 # kg (standard men's shot put)

    # Realistic Thrower Training Notes
    heavy_notes = [
        "Felt solid in the circle today. Good release.",
        "Left knee a bit stiff during warmups, but threw well.",
        "Technique was slightly off on the reverse.",
        "Really explosive today. PR pace.",
        "Felt sluggish, need more sleep. Still got the work in.",
        "Focused on staying low out of the back.",
        "Great session. Implement felt light."
    ]
    
    light_notes = [
        "Just drilling the power position.",
        "Kept it easy. Lots of standing throws.",
        "Felt tight, spent extra time rolling out.",
        "Working on block block arm mechanics.",
        "Good speed work.",
    ]
    
    recovery_notes = [
        "Active recovery. Light stretching, 20min bike.",
        "Sauna and cold plunge.",
        "Complete rest day. Body needed it.",
        "Foam rolling and mobility work only."
    ]

    current_date = start_date
    session_count = 0

    training_days = [] # Track for nutrition

    while session_count < 20 and current_date <= date.today():
        # Schedule: Throwing (Mon, Wed, Fri), Strength (Tue), Recovery (Sat)
        weekday = current_date.weekday()
        
        session_type = 'training'
        intensity = 0
        dur = 0
        best_throw = 0.0

        is_training_day = False

        if weekday in [0, 2, 4]: # Mon, Wed, Fri (Heavy Throwing)
            session_type = 'training'
            intensity = random.uniform(7.5, 9.5)
            dur = random.randint(90, 120)
            
            # Natural linear progression with noise
            progress = (session_count / 20) * 0.8 # up to 0.8m improvement
            noise = random.uniform(-0.3, 0.4)
            best_throw = round(base_throw + progress + noise, 2)
            is_training_day = True

        elif weekday == 1: # Tue (Strength/Technique - lighter)
            session_type = 'training'
            intensity = random.uniform(6.0, 7.5)
            dur = random.randint(60, 90)
            
            # Technique work, slightly shorter throws
            best_throw = round(base_throw - 1.0 + random.uniform(-0.5, 0.5), 2)
            is_training_day = True

        elif weekday == 5: # Sat (Recovery / Active rest)
            session_type = 'recovery'
            intensity = random.uniform(3.0, 5.0)
            dur = random.randint(30, 45)
            # very light technique or no throws
            best_throw = round(base_throw - 4.0, 2)
            is_training_day = True
            
        elif weekday == 6 and session_count == 19: # Last Sunday is Competition
            session_type = 'competition'
            intensity = random.uniform(9.5, 10.0)
            dur = 150
            # Best possible throw
            best_throw = round(base_throw + 1.2 + random.uniform(0.0, 0.3), 2)
            is_training_day = True

        if is_training_day:
            if session_type == 'recovery':
                n_text = random.choice(recovery_notes)
            elif intensity > 8:
                n_text = random.choice(heavy_notes)
            else:
                n_text = random.choice(light_notes)
                
            session = TrainingSession.objects.create(
                user=user,
                date=current_date,
                discipline='shot_put',
                session_type=session_type,
                athlete_type='thrower',
                notes=n_text
            )
            ThrowerSession.objects.create(
                session=session,
                implement_weight_kg=base_weight,
                attempts=random.randint(4, 8),
                best_throw_m=best_throw
            )
            training_days.append((current_date, 'training' if session_type != 'recovery' else 'rest', intensity))
            session_count += 1
            
        current_date += timedelta(days=1)

    print(f"Created {session_count} Training Sessions.")

    # 4. Nutrition Logs (Last 7 days)
    # We look at the last 7 days of the training array (or just date.today() - 6 to today)
    nutrition_start = date.today() - timedelta(days=6)
    
    # Extract intensities for the last 7 days mapping
    intensity_map = {d: i for d, t, i in training_days}
    type_map = {d: t for d, t, i in training_days}

    for i in range(7):
        n_date = nutrition_start + timedelta(days=i)
        
        day_type = type_map.get(n_date, 'rest')
        intensity = intensity_map.get(n_date, 0)

        # Baseline Thrower Macros (High protein, moderate fat, carbs scale with intensity)
        # BMR is roughly ~2200 kcal. Maintenance ~ 2800 kcal. 
        # Heavy training days will push 3800-4500 kcal. Rest days ~ 2800 kcal.

        target_protein = random.uniform(220, 250) # 2g+ per kg
        target_fats = random.uniform(90, 120)
        
        if day_type == 'training' and intensity > 8:
            target_carbs = random.uniform(400, 500) # Heavy carbs
            hydration = random.uniform(4.0, 5.5)
        elif day_type == 'training':
            target_carbs = random.uniform(300, 400) # Moderate carbs
            hydration = random.uniform(3.5, 4.5)
        else:
            target_carbs = random.uniform(200, 250) # Low carbs for rest
            hydration = random.uniform(2.5, 3.5)

        # Split loosely into 4 meals
        splits = {
            'breakfast': 0.25,
            'lunch': 0.30,
            'dinner': 0.35,
            'snack': 0.10
        }

        # Realistic Nutrition Notes
        bfast_notes = ["Oatmeal with whey and peanut butter.", "Eggs, toast, and a huge coffee.", "Skipped - just had a shake.", "Pancakes and syrup. Treat day.", "Standard breakfast bowl."]
        lunch_notes = ["Huge chicken and rice bowl.", "Steak salad with extra dressing.", "Double chicken wrap.", "Leftovers from last night.", "Meal prepped pasta and turkey."]
        dinner_notes = ["Salmon, potatoes, and broccoli.", "Burger and fries.", "Huge bowl of spaghetti.", "Steak and sweet potatoes.", "Chicken, rice, spinach."]
        snack_notes = ["Mass gainer shake.", "Greek yogurt and honey.", "Protein bar and a banana.", "Handful of almonds and beef jerky.", "Extra shake before bed."]

        for meal, fraction in splits.items():
            meal_note = ""
            if meal == "breakfast": meal_note = random.choice(bfast_notes)
            elif meal == "lunch": meal_note = random.choice(lunch_notes)
            elif meal == "dinner": meal_note = random.choice(dinner_notes)
            elif meal == "snack": meal_note = random.choice(snack_notes)

            NutritionLog.objects.create(
                user=user,
                date=n_date,
                day_type=day_type,
                meal_type=meal,
                timing='general',
                carbohydrates_g=round(target_carbs * fraction + random.uniform(-10, 10), 1),
                protein_g=round(target_protein * fraction + random.uniform(-5, 5), 1),
                fats_g=round(target_fats * fraction + random.uniform(-5, 5), 1),
                hydration_liters=round(hydration * fraction, 1),
                notes=meal_note
            )

    print(f"Created 7 Days of Nutrition Logs (28 records).")
    print("Seeding Complete!")

if __name__ == '__main__':
    seed_rahul_data()
