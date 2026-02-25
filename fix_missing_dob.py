import os
import sys
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'athlete_ai_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from users.models import UserProfile

def populate_missing_dob():
    profiles = UserProfile.objects.filter(date_of_birth__isnull=True)
    count = profiles.count()
    if count == 0:
        print("No profiles missing a Date of Birth.")
        return

    today = date.today()
    updated = 0
    
    for profile in profiles:
        # Assign a random age between 18 and 35
        random_age = random.randint(18, 35)
        # Generate a random day offset within that year
        random_days = random.randint(0, 364)
        dob = today.replace(year=today.year - random_age) - timedelta(days=random_days)
        
        profile.date_of_birth = dob
        profile.save(update_fields=['date_of_birth'])
        updated += 1
        
    print(f"Successfully updated {updated} profiles with a random Date of Birth.")

if __name__ == '__main__':
    populate_missing_dob()
