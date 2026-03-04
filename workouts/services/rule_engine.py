import random
from workouts.models import Exercise

def get_discipline_scalar(discipline):
    """Normalize raw ELU across disciplines to a standardized nELU."""
    scalars = {
        'Runner': 1.2,
        'Jumper': 1.0,
        'Thrower': 0.4,
    }
    return scalars.get(discipline, 1.0)

def get_load_zone(target_nelu):
    if target_nelu <= 50:
        return 'Recovery Day'
    elif target_nelu <= 120:
        return 'Moderate Day'
    elif target_nelu <= 200:
        return 'High CNS Day'
    return 'Peak Day'

def get_template(discipline, fatigue_score=0):
    """Returns block allocations roughly mapping to templates."""
    if fatigue_score > 85:
        return [
            {"name": "Recovery Flow", "patterns": ['Mobility', 'Core'], "max_cns": 3.0, "alloc": 1.0}
        ]

    if discipline == 'Thrower':
        return [
            {"name": "Warmup / Activation", "patterns": ['Mobility', 'Core'], "max_cns": 4.0, "alloc": 0.05},
            {"name": "Skill / Throws", "patterns": ['Throw', 'Jump'], "max_cns": 9.5, "alloc": 0.40},
            {"name": "Primary Strength", "patterns": ['Squat', 'Pull', 'Push'], "max_cns": 9.0, "alloc": 0.30},
            {"name": "Secondary Strength", "patterns": ['Hinge', 'Push', 'Pull'], "max_cns": 7.5, "alloc": 0.15},
            {"name": "Accessory / Core", "patterns": ['Core', 'Carry'], "max_cns": 5.0, "alloc": 0.10},
        ]
    elif discipline == 'Jumper':
        return [
            {"name": "Dynamic Warmup", "patterns": ['Mobility'], "max_cns": 5.0, "alloc": 0.10},
            {"name": "Plyo / Jump", "patterns": ['Jump'], "max_cns": 9.5, "alloc": 0.40},
            {"name": "Primary Strength", "patterns": ['Squat', 'Hinge'], "max_cns": 8.5, "alloc": 0.30},
            {"name": "Secondary Strength", "patterns": ['Hinge', 'Core'], "max_cns": 7.0, "alloc": 0.15},
            {"name": "Cooldown", "patterns": ['Mobility'], "max_cns": 3.0, "alloc": 0.05},
        ]
    else: # Runner or default
        return [
            {"name": "Dynamic Warmup", "patterns": ['Mobility', 'Core', 'Sprint'], "max_cns": 5.0, "alloc": 0.10},
            {"name": "Speed / Plyo", "patterns": ['Sprint', 'Jump'], "max_cns": 9.5, "alloc": 0.20},
            {"name": "Primary Conditioning", "patterns": ['Sprint'], "max_cns": 8.5, "alloc": 0.40},
            {"name": "Strength / Accessory", "patterns": ['Squat', 'Hinge', 'Core', 'Pull'], "max_cns": 7.5, "alloc": 0.20},
            {"name": "Cooldown", "patterns": ['Mobility'], "max_cns": 3.0, "alloc": 0.10},
        ]

def find_viable_exercises(discipline, allowed_patterns, max_cns, used_ids, limit_injury_risk=False):
    qs = Exercise.objects.filter(cns_load_score__lte=max_cns)
    
    if allowed_patterns:
        qs = qs.filter(movement_pattern__in=allowed_patterns)
    
    qs = qs.filter(discipline_category__in=[discipline, 'General'])
    
    if used_ids:
        qs = qs.exclude(exercise_id__in=used_ids)

    if limit_injury_risk:
        qs = qs.exclude(injury_risk_level='High')
        
    return list(qs)

def optimize_volume(exercise, target_raw_elu):
    """Finds sets/reps mapping inside recommended constraints."""
    best_diff = float('inf')
    best_sets = exercise.recommended_min_sets
    best_reps = exercise.recommended_min_reps

    for s in range(exercise.recommended_min_sets, exercise.recommended_max_sets + 1):
        for r in range(exercise.recommended_min_reps, exercise.recommended_max_reps + 1):
            elu = (s * r) * exercise.cns_load_score * exercise.intensity_multiplier
            diff = abs(target_raw_elu - elu)
            if diff < best_diff:
                best_diff = diff
                best_sets = s
                best_reps = r

    return best_sets, best_reps

def build_session(discipline, fatigue_score, target_load):
    """
    discipline: String, e.g. 'Runner', 'Thrower', 'Jumper'
    fatigue_score: Float 0-100
    target_load: Float (target nELU from ML)
    """
    scalar = get_discipline_scalar(discipline)
    target_nelu = target_load
    zone = get_load_zone(target_nelu)
    template = get_template(discipline, fatigue_score)

    max_cns_cap = 9.5
    limit_injury_risk = False
    
    if fatigue_score > 70: 
        max_cns_cap = 7.5
        limit_injury_risk = True

    if fatigue_score > 85: 
        max_cns_cap = 5.0 # Forces recovery explicitly via template anyway

    session_plan = []
    total_nelu_generated = 0.0
    used_exercise_ids = set()

    for block in template:
        # Stop overall session generation if we hit ~95% of total target load
        if total_nelu_generated >= target_nelu * 0.95:
            break

        block_nelu_target = target_nelu * block['alloc']
        if block_nelu_target < 1: 
            continue

        block_nelu_generated = 0.0
        consecutive_failures = 0

        # Fill block until reaching ~95% of its target
        while block_nelu_generated < block_nelu_target * 0.95 and consecutive_failures < 3:
            remaining_block_nelu = block_nelu_target - block_nelu_generated
            remaining_raw_elu = remaining_block_nelu / scalar

            viable_exercises = find_viable_exercises(
                discipline=discipline,
                allowed_patterns=block['patterns'],
                max_cns=min(block['max_cns'], max_cns_cap),
                used_ids=used_exercise_ids,
                limit_injury_risk=limit_injury_risk
            )

            if not viable_exercises:
                # Need a fallback
                fallback_patterns = ['Mobility', 'Core']
                viable_exercises = find_viable_exercises(
                    discipline=discipline,
                    allowed_patterns=fallback_patterns,
                    max_cns=3.0,
                    used_ids=used_exercise_ids,
                    limit_injury_risk=True
                )
                if not viable_exercises:
                    break

            # Pick randomly from the top 3 highest CNS exercises that fit remaining constraints
            viable_exercises.sort(key=lambda x: x.cns_load_score, reverse=True)
            selected_exercise = random.choice(viable_exercises[:3])

            used_exercise_ids.add(selected_exercise.exercise_id)

            sets, reps = optimize_volume(selected_exercise, remaining_raw_elu)
            generated_raw_elu = selected_exercise.calculate_elu(sets, reps)
            generated_nelu = generated_raw_elu * scalar

            if generated_nelu == 0:
                consecutive_failures += 1
                continue

            session_plan.append({
                "block": block['name'],
                "exercise": selected_exercise.exercise_name,
                "sets": sets,
                "reps": reps,
                "rest": selected_exercise.rest_time_seconds_max
            })

            block_nelu_generated += generated_nelu
            consecutive_failures = 0

        total_nelu_generated += block_nelu_generated

    return {
        "day_type": zone,
        "total_nelu": round(total_nelu_generated, 1),
        "blocks": session_plan
    }
