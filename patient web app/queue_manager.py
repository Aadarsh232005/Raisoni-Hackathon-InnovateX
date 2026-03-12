from datetime import datetime

patients   = []
queue      = []
iot_data   = {}
_token_seq = [1]

doctors = [
    {"id": 1, "name": "Dr. Priya Sharma",  "specialty": "General Medicine", "available": True,  "room": "Room 101"},
    {"id": 2, "name": "Dr. Arjun Mehta",   "specialty": "Cardiology",       "available": True,  "room": "Room 102"},
    {"id": 3, "name": "Dr. Sunita Reddy",  "specialty": "Pediatrics",       "available": True,  "room": "Room 103"},
    {"id": 4, "name": "Dr. Vikram Nair",   "specialty": "Orthopedics",      "available": False, "room": "Room 104"},
]

def _next_token():
    t = _token_seq[0]
    _token_seq[0] += 1
    return t

def _now():
    return datetime.now().strftime("%H:%M:%S")

def _rebuild_positions():
    active    = [p for p in queue if p["status"] == "active"]
    high_wait = [p for p in queue if p["status"] == "waiting" and p["priority"] == "HIGH"]
    norm_wait = [p for p in queue if p["status"] == "waiting" and p["priority"] == "NORMAL"]
    done      = [p for p in queue if p["status"] == "completed"]
    ordered   = active + high_wait + norm_wait + done
    pos = 1
    for p in ordered:
        if p["status"] == "waiting":
            p["position"]       = pos
            p["estimated_wait"] = (pos - 1) * 5
            pos += 1
        elif p["status"] == "active":
            p["position"]       = 0
            p["estimated_wait"] = 0
    return ordered

def add_patient(name, age, phone, symptoms, doctor_id, appt_time):
    doctor = next((d for d in doctors if d["id"] == int(doctor_id)), doctors[0])
    token  = _next_token()

    # Count only waiting patients for position
    waiting_count = len([p for p in queue if p["status"] == "waiting"])
    active_count  = len([p for p in queue if p["status"] == "active"])

    patient = {
        "id":             len(patients) + 1,
        "token":          token,
        "name":           name,
        "age":            int(age),
        "phone":          phone,
        "symptoms":       symptoms,
        "doctor_id":      int(doctor_id),
        "doctor_name":    doctor["name"],
        "doctor_room":    doctor["room"],
        "appt_time":      appt_time,
        "status":         "waiting",
        "priority":       "NORMAL",
        "position":       waiting_count + 1,
        "estimated_wait": waiting_count * 5,
        "registered_at":  _now(),
        "vitals":         {"temperature": 98.6, "heart_rate": 72},
        "completed_at":   None,
        "activated_at":   None,
    }

    patients.append(patient)
    queue.append(patient)

    # If nobody is active yet, make this patient active immediately
    if active_count == 0:
        patient["status"]       = "active"
        patient["activated_at"] = _now()

    _rebuild_positions()
    return patient

def get_queue():
    return _rebuild_positions()

def complete_patient(token):
    target = None
    for p in queue:
        if p["token"] == int(token) and p["status"] == "active":
            target = p
            break

    if not target:
        return False

    target["status"]       = "completed"
    target["completed_at"] = _now()
    _activate_next()
    return True

def _activate_next():
    waiting = [p for p in queue if p["status"] == "waiting"]
    high    = [p for p in waiting if p["priority"] == "HIGH"]
    nxt     = high[0] if high else (waiting[0] if waiting else None)
    if nxt:
        nxt["status"]       = "active"
        nxt["activated_at"] = _now()
    return nxt

def update_iot(data):
    global iot_data
    iot_data = {
        "temperature":        float(data.get("temperature", 25)),
        "humidity":           float(data.get("humidity", 50)),
        "motion_detected":    bool(data.get("motion_detected", False)),
        "waiting_room_count": int(data.get("waiting_room_count", 0)),
        "timestamp":          _now(),
    }
    pid = data.get("patient_id")
    if pid:
        for p in patients:
            if p["id"] == pid or p["token"] == pid:
                p["vitals"]["temperature"] = float(data.get("temperature", 98.6))
                p["vitals"]["heart_rate"]  = float(data.get("heart_rate", 72))
                if p["vitals"]["temperature"] > 100 or p["vitals"]["heart_rate"] > 100:
                    if p["status"] != "completed":
                        p["priority"] = "HIGH"
    return iot_data

def get_stats():
    return {
        "total_today":       len(patients),
        "waiting":           len([p for p in queue if p["status"] == "waiting"]),
        "active":            len([p for p in queue if p["status"] == "active"]),
        "high_priority":     len([p for p in queue if p["priority"] == "HIGH" and p["status"] != "completed"]),
        "completed":         len([p for p in queue if p["status"] == "completed"]),
        "available_doctors": len([d for d in doctors if d["available"]]),
        "crowd_count":       iot_data.get("waiting_room_count", 0),
        "doctors":           doctors,
        "iot":               iot_data,
    }

def get_active():
    return next((p for p in queue if p["status"] == "active"), None)

def get_next():
    waiting = [p for p in queue if p["status"] == "waiting"]
    high    = [p for p in waiting if p["priority"] == "HIGH"]
    return high[0] if high else (waiting[0] if waiting else None)

def export_all():
    return {
        "patients":    patients,
        "queue":       _rebuild_positions(),
        "iot_data":    iot_data,
        "doctors":     doctors,
        "stats":       get_stats(),
        "exported_at": datetime.now().isoformat(),
    }