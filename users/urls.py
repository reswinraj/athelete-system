from django.urls import path
from .views import (
    profile_view, edit_profile, login_page, signup_page, logout_view, 
    dashboard_view, insights_view, coach_dashboard_view, 
    coach_athlete_detail_view, coach_athlete_workouts_view, 
    coach_athlete_detail_view, coach_athlete_workouts_view, 
    coach_athlete_detail_view, coach_athlete_workouts_view, 
    coach_athlete_nutrition_view, coach_assign_athlete_view,
    coach_give_suggestion_view, athlete_suggestions_view,
    generate_performance_rf_view, generate_training_rf_view, generate_nutrition_rf_view
)

urlpatterns = [
    path("login/", login_page, name="login"),
    path("signup/", signup_page, name="signup"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile_view, name="user_profile"),
    path("profile/edit/", edit_profile, name="edit_profile"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("dashboard/suggestions/", athlete_suggestions_view, name="athlete_suggestions"),
    path("insights/", insights_view, name="insights"),
    
    # Coach URLs
    path("coach/dashboard/", coach_dashboard_view, name="coach_dashboard"),
    path("coach/athlete/<int:pk>/", coach_athlete_detail_view, name="coach_athlete_detail"),
    path("coach/athlete/<int:pk>/workouts/", coach_athlete_workouts_view, name="coach_athlete_workouts"),
    path("coach/athlete/<int:pk>/nutrition/", coach_athlete_nutrition_view, name="coach_athlete_nutrition"),
    path("coach/assign-athlete/", coach_assign_athlete_view, name="coach_assign_athlete"),
    path("coach/athlete/<int:athlete_id>/suggest/", coach_give_suggestion_view, name="coach_give_suggestion"),
    
    # AI RF Generator endpoints
    path("generate-performance-rf/", generate_performance_rf_view, name="generate_performance_rf"),
    path("generate-training-rf/", generate_training_rf_view, name="generate_training_rf"),
    path("generate-nutrition-rf/", generate_nutrition_rf_view, name="generate_nutrition_rf"),
]
