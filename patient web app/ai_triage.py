CRITICAL_KEYWORDS = [
    "chest pain", "breathless", "unconscious", "severe pain",
    "bleeding", "stroke", "heart attack", "difficulty breathing",
    "seizure", "cannot breathe", "fainted",
]

def assess_priority(temperature=98.6, heart_rate=72, symptoms=""):
    reasons = []
    priority = "NORMAL"
    if float(temperature) > 100:
        priority = "HIGH"
        reasons.append(f"Fever: {temperature}°F")
    if float(heart_rate) > 100:
        priority = "HIGH"
        reasons.append(f"High heart rate: {heart_rate} bpm")
    sym = symptoms.lower()
    for kw in CRITICAL_KEYWORDS:
        if kw in sym:
            priority = "HIGH"
            reasons.append(f"Critical symptom: '{kw}'")
            break
    return {"priority": priority, "reasons": reasons}

def predict_wait(position, avg_min=5):
    return max(0, (position - 1) * avg_min)