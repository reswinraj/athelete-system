from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Avg, Sum, Max
from django.core.paginator import Paginator
from .models import UserProfile, Suggestion
from .forms import UserProfileForm, SignupForm, LoginForm, AssignCoachForm, SuggestionForm
# Import metrics models
from workouts.models import TrainingSession
from meals.models import NutritionLog
from .decorators import athlete_required, coach_required, get_role_redirect
@athlete_required
def dashboard_view(request):
    """
    Main dashboard for the athlete.
    """
    # 1. Training Stats
    training_qs = TrainingSession.objects.filter(user=request.user)
    training_count = training_qs.count()
    last_training = training_qs.order_by('-date').first()
    # 2. Nutrition Stats
    nutrition_qs = NutritionLog.objects.filter(user=request.user)
    nutrition_count = nutrition_qs.count()
    last_nutrition = nutrition_qs.order_by('-date').first()
    context = {
        'user': request.user,
        'training_count': training_count,
        'last_training_date': last_training.date if last_training else None,
        'nutrition_count': nutrition_count,
        'last_nutrition_date': last_nutrition.date if last_nutrition else None,
    }
    return render(request, "users/dashboard.html", context)
from .ml_utils import analyze_performance_trend
from .plan_generator import generate_training_plan, generate_diet_plan
@login_required
def insights_view(request):
    """
    Generate deterministic, rule-based insights.
    NO ML, NO AI. Just logic.
    """
    insights = []
    # --- ML TREND ANALYSIS (Step 10) ---
    try:
        ml_insight = analyze_performance_trend(request.user)
        if ml_insight:
            insights.append(ml_insight)
    except Exception as e:
        # Graceful failure if libraries missing or data issue
        insights.append(f"AI Analysis unavailable: {e}")
    # --- Rule 1: Runner Fueling & Performance ---
    # Need last 6 sessions of a specific discipline (e.g. user's main event?).
    # Simplify: Check ALL runner sessions, group by discipline?
    # For MVP: Pick the discipline of the most recent session.
    sessions = TrainingSession.objects.filter(user=request.user, athlete_type='runner').order_by('-date')
    if sessions.exists():
        recent_discipline = sessions.first().discipline
        # Get last 6 sessions of this discipline
        discipline_sessions = list(sessions.filter(discipline=recent_discipline)[:6])
        if len(discipline_sessions) >= 2:
            half_window = max(1, len(discipline_sessions) // 2)
            recent_slice = discipline_sessions[:half_window]
            prev_slice = discipline_sessions[half_window : half_window * 2]
            # Times (Assuming 'runnersession' exists)
            # Filter out sessions without runnersession or 0 time
            recent_times = [s.runnersession.time_seconds for s in recent_slice if hasattr(s, 'runnersession') and s.runnersession.time_seconds > 0]
            prev_times = [s.runnersession.time_seconds for s in prev_slice if hasattr(s, 'runnersession') and s.runnersession.time_seconds > 0]
            if len(recent_times) >= 1 and len(prev_times) >= 1:
                avg_recent = sum(recent_times) / len(recent_times)
                avg_prev = sum(prev_times) / len(prev_times)
                # Check performance decline (Time increased)
                if avg_recent > avg_prev * 1.02: # 2% margin to be sure
                    # Check Fueling
                    # Avg Daily Carbs on Training Days
                    daily_carbs = NutritionLog.objects.filter(
                        user=request.user, 
                        day_type='training'
                    ).values('date').annotate(total_carbs=Sum('carbohydrates_g'))
                    if daily_carbs.count() >= 2:
                        avg_carbs = sum(d['total_carbs'] for d in daily_carbs) / len(daily_carbs)
                        if avg_carbs < 250:
                             insights.append(f"<b>Fueling Alert ({recent_discipline}):</b> Your recent times avg {avg_recent:.2f}s (vs {avg_prev:.2f}s prev). Your average training day carbs are {avg_carbs:.0f}g. Increasing carbohydrate intake may help recovery.")
    # --- Rule 2: Jumper Plateau ---
    jump_sessions = TrainingSession.objects.filter(user=request.user, athlete_type='jumper').order_by('-date')
    if jump_sessions.exists():
         # Pick recent discipline
        recent_discipline = jump_sessions.first().discipline
        j_sessions = list(jump_sessions.filter(discipline=recent_discipline)[:5])
        if len(j_sessions) >= 2:
            # Check best jumps
            recent_jumps = [s.jumpersession.best_jump_m for s in j_sessions if hasattr(s, 'jumpersession')]
            if len(recent_jumps) >= 2:
                half_window = max(1, len(recent_jumps) // 2)
                recent_max = max(recent_jumps[:half_window])
                prev_max = max(recent_jumps[half_window:])
                if recent_max <= prev_max:
                     insights.append(f"<b>Plateau Detected ({recent_discipline}):</b> Your best jump in the last {half_window} sessions ({recent_max}m) hasn't exceeded your previous marker ({prev_max}m). Consider reviewing technique or rest periods.")
    # --- Rule 3: Thrower Load Impact ---
    throw_sessions = TrainingSession.objects.filter(user=request.user, athlete_type='thrower').order_by('-date')
    if throw_sessions.exists():
         recent_discipline = throw_sessions.first().discipline
         t_sessions = list(throw_sessions.filter(discipline=recent_discipline)[:4])
         if len(t_sessions) >= 2:
             half_window = max(1, len(t_sessions) // 2)
             recent_slice = t_sessions[:half_window]
             prev_slice = t_sessions[half_window : half_window * 2]
             try:
                 avg_weight_recent = sum(s.throwersession.implement_weight_kg for s in recent_slice) / len(recent_slice)
                 avg_weight_prev = sum(s.throwersession.implement_weight_kg for s in prev_slice) / len(prev_slice)
                 avg_dist_recent = sum(s.throwersession.best_throw_m for s in recent_slice) / len(recent_slice)
                 avg_dist_prev = sum(s.throwersession.best_throw_m for s in prev_slice) / len(prev_slice)
                 if avg_weight_recent > avg_weight_prev and avg_dist_recent < avg_dist_prev:
                     insights.append(f"<b>Load Impact ({recent_discipline}):</b> Implement weight increased ({avg_weight_prev}kg -> {avg_weight_recent}kg) but distance dropped ({avg_dist_prev}m -> {avg_dist_recent}m). Ensure technique is maintained under load.")
             except:
                 pass # Handle missing child data safely
    # --- Step 4: Generate Automatic Plans ---
    # We append these regardless of other alerts, as they are "Suggestions"
    try:
        training_plan = generate_training_plan(request.user)
        if training_plan:
            insights.append(training_plan)
        diet_plan = generate_diet_plan(request.user)
        if diet_plan:
            insights.append(diet_plan)
    except Exception as e:
        insights.append(f"Error generating plans: {e}")
    if not insights:
        insights.append("Log at least 2 sessions and 2 meals to see performance insights.")
        
    try:
        profile = request.user.userprofile
    except Exception:
        profile = None
        
    return render(request, "users/insights.html", {'insights': insights, 'profile': profile})
def login_page(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect(request.user)) # Redirect based on role
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username_or_email, password=password)
            if user is not None:
                login(request, user)
                return redirect(get_role_redirect(user))
            else:
                messages.error(request, "Invalid username/email or password.")
    else:
        form = LoginForm()
    return render(request, "login.html", {'form': form})
def signup_page(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect(request.user))
    if request.method == "POST":
        import traceback
        with open('c:/project02/signup_debug.log', 'a') as f:
            f.write(f"\\n--- Signup Request {request.method} ---")
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                with open('c:/project02/signup_debug.log', 'a') as f:
                     f.write("\\nForm valid. Saving...")
                user = form.save()
                with open('c:/project02/signup_debug.log', 'a') as f:
                     f.write(f"\\nUser saved: {user.username} (id: {user.id})")
                
                # Check profile
                has_profile = hasattr(user, 'userprofile')
                role = "N/A"
                if has_profile:
                    role = user.userprofile.role
                with open('c:/project02/signup_debug.log', 'a') as f:
                     f.write(f"\\nHas Profile: {has_profile}. Role: {role}")

                login(request, user, backend='users.backends.EmailOrUsernameBackend')
                messages.success(request, f"Account created! Welcome, {user.username}.")
                
                redir = get_role_redirect(user)
                with open('c:/project02/signup_debug.log', 'a') as f:
                     f.write(f"\\nRedirecting to: {redir}")
                
                return redirect(redir)
            except Exception as e:
                with open('c:/project02/signup_debug.log', 'a') as f:
                     f.write(f"\\nEXCEPTION: {e}\\n{traceback.format_exc()}")
                messages.error(request, f"Error creating account: {e}")
        else:
            with open('c:/project02/signup_debug.log', 'a') as f:
                 f.write(f"\\nForm Invalid: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignupForm()
    return render(request, "signup.html", {'form': form})
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")
def main_page(request):
    return render(request, "main.html")
@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    context = {'profile': profile, 'user': request.user}
    return render(request, 'users/profile.html', context)
@login_required
def edit_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        try:
            profile.date_of_birth = request.POST.get('date_of_birth') or None
            profile.gender = request.POST.get('gender')
            profile.sport = request.POST.get('sport')
            profile.height_cm = request.POST.get('height_cm') or None
            profile.weight_kg = request.POST.get('weight_kg') or None
            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('user_profile')
        except Exception as e:
            messages.error(request, f"Error updating profile: {e}")
    context = {'profile': profile, 'user': request.user}
    return render(request, 'users/edit_profile.html', context)
# --- Coach Views ---

@coach_required
def coach_dashboard_view(request):
    """
    Coach Dashboard: List all assigned athletes and their quick stats.
    """
    # Get the coach's profile
    coach_profile = request.user.userprofile
    
    # 1. Fetch assigned athletes
    assigned_athletes = coach_profile.athletes.select_related('user').all()
    
    # 2. Fetch ALL athletes (regardless of coach)
    all_athletes = UserProfile.objects.filter(role='Athlete').select_related('user').order_by('-id')
    
    # 3. Fetch unassigned athletes (for quick actions)
    unassigned_athletes = UserProfile.objects.filter(role='Athlete', coach__isnull=True).select_related('user')

    context = {
        'athletes': assigned_athletes,  # Keep existing key for backward compatibility or rename in template
        'assigned_athletes': assigned_athletes,
        'all_athletes': all_athletes,
        'unassigned_athletes': unassigned_athletes
    }
    return render(request, 'users/coach/dashboard.html', context)
@coach_required
def coach_athlete_detail_view(request, pk):
    """
    Detailed view of a specific athlete for the coach.
    """
    # 3. Secure Access Control: Ensure athlete belongs to THIS coach
    athlete = get_object_or_404(UserProfile, pk=pk, coach=request.user.userprofile)
    context = {
        'athlete': athlete,
        'user': athlete.user # Pass user easily
    }
    return render(request, 'users/coach/athlete_detail.html', context)
@coach_required
def coach_athlete_workouts_view(request, pk):
    """
    Read-only view of athlete's training logs (detailed cards).
    """
    athlete_profile = get_object_or_404(UserProfile, pk=pk, coach=request.user.userprofile)
    athlete_user = athlete_profile.user

    # Optimised query: fetch sub-session data in one shot
    queryset = TrainingSession.objects.filter(user=athlete_user).select_related(
        'runnersession',
        'throwersession',
        'jumpersession'
    ).order_by('-date')

    # --- Personal Best detection (thrower) ---
    pb_session_id = None
    pb_agg = queryset.filter(throwersession__isnull=False).aggregate(
        max_throw=Max('throwersession__best_throw_m')
    )
    if pb_agg['max_throw'] is not None:
        pb_qs = queryset.filter(
            throwersession__best_throw_m=pb_agg['max_throw']
        ).first()
        if pb_qs:
            pb_session_id = pb_qs.id

    # --- Pace calculation (attached to session objects) ---
    for session in queryset:
        rs = getattr(session, 'runnersession', None)
        if rs is not None and rs.distance_m and rs.distance_m > 0:
            pace_seconds = rs.time_seconds / (rs.distance_m / 1000.0)
            mins = int(pace_seconds // 60)
            secs = int(pace_seconds % 60)
            session.pace_per_km = f"{mins}:{secs:02d}"
        else:
            session.pace_per_km = None

    # --- Pagination ---
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'athlete': athlete_profile,
        'sessions_page': page_obj,
        'pb_session_id': pb_session_id,
        'is_paginated': paginator.num_pages > 1,
    }
    return render(request, 'users/coach/athlete_workouts.html', context)

@coach_required
def coach_athlete_nutrition_view(request, pk):
    """
    Read-only view of athlete's nutrition logs (detailed cards).
    """
    athlete_profile = get_object_or_404(UserProfile, pk=pk, coach=request.user.userprofile)
    athlete_user = athlete_profile.user

    # Optimised query: prefetch food items
    queryset = NutritionLog.objects.filter(user=athlete_user).prefetch_related(
        'items__food_item'
    ).order_by('-date')

    # --- Compute per-log totals (items take priority; fallback to legacy fields) ---
    for log in queryset:
        items = list(log.items.all())
        if items:
            log.total_carbs = sum(i.carbohydrates_g for i in items)
            log.total_protein = sum(i.protein_g for i in items)
            log.total_fats = sum(i.fats_g for i in items)
        else:
            log.total_carbs = log.carbohydrates_g
            log.total_protein = log.protein_g
            log.total_fats = log.fats_g

    # --- Pagination ---
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'athlete': athlete_profile,
        'logs_page': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }
    return render(request, 'users/coach/athlete_nutrition.html', context)

@coach_required
def coach_assign_athlete_view(request):
    """
    Coach: Add (Assign) an athlete to themselves or another coach.
    Typically, a coach would pick an unassigned athlete.
    """
    if request.method == 'POST':
        # Simple flow: Coach enters username or selects from unassigned list
        # For this MVP, let's assume we are assigning a specific athlete ID passed via GET/POST
        # OR, we list unassigned athletes and have an "Add" button.
        
        # Let's implement: List unassigned athletes -> Click "Add" -> Assigns to current coach
        pass 
    
    # Get all unassigned athletes
    unassigned_athletes = UserProfile.objects.filter(role='Athlete', coach__isnull=True)
    
    if request.method == 'POST':
        athlete_id = request.POST.get('athlete_id')
        if athlete_id:
            athlete = get_object_or_404(UserProfile, id=athlete_id, role='Athlete')
            athlete.coach = request.user.userprofile
            athlete.save()
            print(f"[ACTION] Coach {request.user.username} assigned athlete {athlete.user.username} (ID: {athlete.id}) to themselves.")
            messages.success(request, f"Athlete {athlete.user.username} assigned to you.")
            return redirect('coach_dashboard')
            
    context = {
        'unassigned_athletes': unassigned_athletes
    }
    return render(request, 'users/coach/assign_athlete.html', context)

@coach_required
def coach_give_suggestion_view(request, athlete_id):
    """
    Coach: Give a suggestion to a specific assigned athlete.
    """
    # Verify athlete belongs to this coach
    athlete_profile = get_object_or_404(UserProfile, user_id=athlete_id, coach=request.user.userprofile)
    athlete_user = athlete_profile.user
    
    if request.method == 'POST':
        form = SuggestionForm(request.POST)
        if form.is_valid():
            suggestion = form.save(commit=False)
            suggestion.coach = request.user
            suggestion.athlete = athlete_user
            suggestion.save()
            messages.success(request, f"Suggestion sent to {athlete_user.username}!")
            return redirect('coach_athlete_detail', pk=athlete_profile.pk)
    else:
        form = SuggestionForm()
    
    context = {
        'form': form,
        'athlete': athlete_profile
    }
    return render(request, 'users/coach/suggestion_form.html', context)

@athlete_required
def athlete_suggestions_view(request):
    """
    Athlete: View suggestions from their coach.
    """
    suggestions = Suggestion.objects.filter(athlete=request.user).order_by('-created_at')
    
    context = {
        'suggestions': suggestions
    }
    return render(request, 'users/athlete_suggestions.html', context)

