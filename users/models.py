from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- Existing Models (Preserved) ---
class AthleteProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    SPORT_GROUP_CHOICES = [('runner', 'Runner'), ('thrower', 'Thrower'), ('jumper', 'Jumper')]
    RUNNER_EVENTS = [('100m', '100m Sprint'), ('200m', '200m Sprint'), ('400m', '400m Sprint'), ('800m', '800m'), ('1500m', '1500m'), ('3000m', '3000m'), ('5000m', '5000m'), ('10000m', '10000m')]
    THROWER_EVENTS = [('shotput', 'Shot Put'), ('javelin', 'Javelin Throw'), ('hammer', 'Hammer Throw')]
    JUMPER_EVENTS = [('long_jump', 'Long Jump'), ('high_jump', 'High Jump')]
    EVENT_CHOICES = RUNNER_EVENTS + THROWER_EVENTS + JUMPER_EVENTS
    EXPERIENCE_CHOICES = [('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')]
    TRAINING_GOAL_CHOICES = [('endurance', 'Endurance'), ('performance', 'Performance'), ('fat_loss', 'Fat Loss'), ('strength', 'Strength')]
    sport_group = models.CharField(max_length=20, choices=SPORT_GROUP_CHOICES)
    sport_event = models.CharField(max_length=50, choices=EVENT_CHOICES)
    age = models.IntegerField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES)
    training_goal = models.CharField(max_length=20, choices=TRAINING_GOAL_CHOICES)
    def bmi(self):
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 2)
        return None
    def __str__(self): return f"{self.user.username} Profile"

class CoachProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100, blank=True)
    def __str__(self): return f"Coach: {self.user.username}"

# --- New UserProfile Model (The Active One) ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    ROLE_CHOICES = [
        ('Athlete', 'Athlete'),
        ('Coach', 'Coach'),
    ]
    
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    sport = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Athlete')
    coach = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='athletes',
        limit_choices_to={'role': 'Coach'},
        help_text="The coach assigned to this athlete"
    )
    
    @property
    def age(self):
        if self.date_of_birth:
            import datetime
            today = datetime.date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    def bmi(self):
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            if h > 0:
                return round(self.weight_kg / (h * h), 2)
        return None

    def __str__(self):
        return f"{self.user.username} Profile"

class Suggestion(models.Model):
    """
    Model for feedback/suggestions from a Coach to an Athlete.
    """
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_suggestions')
    athlete = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_suggestions')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Suggestion from {self.coach.username} to {self.athlete.username} on {self.created_at.strftime('%Y-%m-%d')}"

# --- Signals ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        import traceback
        try:
            profile = UserProfile.objects.create(user=instance)
            # Log successful creation
            print(f"[SIGNAL] Created UserProfile for {instance.username} (ID: {instance.id})")
        except Exception as e:
            print(f"[SIGNAL] ERROR creating UserProfile for {instance.username}: {e}")
            traceback.print_exc()

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists before saving
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
