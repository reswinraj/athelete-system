from django.db import models
from django.contrib.auth.models import User

# --- Base Session Model ---
class TrainingSession(models.Model):
    SESSION_TYPES = [
        ('training', 'Training'),
        ('competition', 'Competition'),
        ('recovery', 'Recovery'),
    ]

    DISCIPLINES = [
        # Track
        ('100m', '100m Sprint'),
        ('200m', '200m Sprint'),
        ('400m', '400m Sprint'),
        ('800m', '800m Run'),
        ('1500m', '1500m Run'),
        # Jumps
        ('long_jump', 'Long Jump'),
        ('high_jump', 'High Jump'),
        ('triple_jump', 'Triple Jump'),
        # Throws
        ('shot_put', 'Shot Put'),
        ('discus', 'Discus Throw'),
        ('javelin', 'Javelin Throw'),
        ('hammer', 'Hammer Throw'),
    ]

    ATHLETE_TYPES = [
        ('runner', 'Runner'),
        ('jumper', 'Jumper'),
        ('thrower', 'Thrower'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    discipline = models.CharField(max_length=20, choices=DISCIPLINES)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='training')
    athlete_type = models.CharField(max_length=20, choices=ATHLETE_TYPES)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.discipline} ({self.date})"

    @property
    def specific_session(self):
        """Helper to get the child object"""
        if hasattr(self, 'runnersession'): return self.runnersession
        if hasattr(self, 'jumpersession'): return self.jumpersession
        if hasattr(self, 'throwersession'): return self.throwersession
        return None


# --- Event Specific Models ---

class RunnerSession(models.Model):
    session = models.OneToOneField(TrainingSession, on_delete=models.CASCADE)
    distance_m = models.FloatField(help_text="Distance in meters (e.g., 100, 200)")
    time_seconds = models.FloatField(help_text="Time in seconds")
    repetitions = models.IntegerField(default=1, help_text="Number of reps")

    def __str__(self):
        return f"Run: {self.distance_m}m x {self.repetitions}"

class JumperSession(models.Model):
    session = models.OneToOneField(TrainingSession, on_delete=models.CASCADE)
    attempts = models.IntegerField(default=1)
    best_jump_m = models.FloatField(help_text="Best result in meters")

    def __str__(self):
        return f"Jump: {self.best_jump_m}m (Best)"

class ThrowerSession(models.Model):
    session = models.OneToOneField(TrainingSession, on_delete=models.CASCADE)
    implement_weight_kg = models.FloatField(help_text="Weight of implement in kg")
    attempts = models.IntegerField(default=1)
    best_throw_m = models.FloatField(help_text="Best result in meters")

    def __str__(self):
        return f"Throw: {self.best_throw_m}m ({self.implement_weight_kg}kg)"

# --- Exercise Database Model ---

class Exercise(models.Model):
    DISCIPLINE_CHOICES = [
        ('Runner', 'Runner'),
        ('Jumper', 'Jumper'),
        ('Thrower', 'Thrower'),
        ('General', 'General'),
    ]

    MOVEMENT_PATTERN_CHOICES = [
        ('Squat', 'Squat'),
        ('Hinge', 'Hinge'),
        ('Push', 'Push'),
        ('Pull', 'Pull'),
        ('Carry', 'Carry'),
        ('Sprint', 'Sprint'),
        ('Jump', 'Jump'),
        ('Throw', 'Throw'),
        ('Core', 'Core'),
        ('Mobility', 'Mobility'),
    ]

    ENERGY_SYSTEM_CHOICES = [
        ('ATP-PC', 'ATP-PC'),
        ('Glycolytic', 'Glycolytic'),
        ('Oxidative', 'Oxidative'),
    ]

    INTENSITY_CHOICES = [
        ('Strength', 'Strength'),
        ('Power', 'Power'),
        ('Hypertrophy', 'Hypertrophy'),
        ('Conditioning', 'Conditioning'),
        ('Recovery', 'Recovery'),
    ]

    EQUIPMENT_CHOICES = [
        ('None', 'None'),
        ('Barbell', 'Barbell'),
        ('Dumbbell', 'Dumbbell'),
        ('Kettlebell', 'Kettlebell'),
        ('Bands', 'Bands'),
        ('Machine', 'Machine'),
        ('Track', 'Track'),
        ('Field', 'Field'),
        ('Medicine Ball', 'Medicine Ball'),
    ]

    LATERALITY_CHOICES = [
        ('Unilateral', 'Unilateral'),
        ('Bilateral', 'Bilateral'),
        ('N/A', 'N/A'),
    ]

    COMPLEXITY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    RISK_CHOICES = [
        ('Low', 'Low'),
        ('Moderate', 'Moderate'),
        ('High', 'High'),
    ]

    exercise_id = models.CharField(max_length=50, primary_key=True)
    exercise_name = models.CharField(max_length=100)
    discipline_category = models.CharField(max_length=20, choices=DISCIPLINE_CHOICES)
    movement_pattern = models.CharField(max_length=50, choices=MOVEMENT_PATTERN_CHOICES)
    primary_muscle_group = models.CharField(max_length=50)
    energy_system = models.CharField(max_length=20, choices=ENERGY_SYSTEM_CHOICES)
    cns_load_score = models.FloatField(help_text="1.0 to 10.0 scale")
    intensity_type = models.CharField(max_length=20, choices=INTENSITY_CHOICES)
    recommended_min_sets = models.IntegerField(default=1)
    recommended_max_sets = models.IntegerField(default=5)
    recommended_min_reps = models.IntegerField(default=1)
    recommended_max_reps = models.IntegerField(default=20)
    rest_time_seconds_min = models.IntegerField(default=60)
    rest_time_seconds_max = models.IntegerField(default=180)
    equipment_required = models.CharField(max_length=50, choices=EQUIPMENT_CHOICES, default='None')
    unilateral_or_bilateral = models.CharField(max_length=20, choices=LATERALITY_CHOICES, default='Bilateral')
    complexity_level = models.CharField(max_length=20, choices=COMPLEXITY_CHOICES, default='Intermediate')
    injury_risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default='Moderate')

    @property
    def intensity_multiplier(self):
        mul_map = {
            'Recovery': 0.8,
            'Conditioning': 1.0,
            'Hypertrophy': 1.2,
            'Strength': 1.5,
            'Power': 1.8,
        }
        return mul_map.get(self.intensity_type, 1.0)

    def calculate_elu(self, sets, reps):
        """ Calculate Estimated Load Units (ELU) using formula: (Sets * Reps) * CNS_Load * Intensity_Multiplier """
        return (sets * reps) * self.cns_load_score * self.intensity_multiplier

    def __str__(self):
        return f"[{self.exercise_id}] {self.exercise_name} ({self.discipline_category})"
