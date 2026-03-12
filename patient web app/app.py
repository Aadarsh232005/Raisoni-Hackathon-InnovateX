from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
import queue_manager as qm
import auth as Auth
import sms_service as sms
import voice_module as vm
import ai_triage as triage

app = Flask(__name__)
app.secret_key = "smart_hospital_secret_2024"

# ─── Index ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        role = session.get("role")
        if role == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        if role == "DOCTOR":
            return redirect(url_for("doctor_dashboard"))
        return redirect(url_for("patient_dashboard"))
    return redirect(url_for("login"))

# ─── Auth routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = Auth.authenticate(username, password)
        if user:
            session["user_id"]   = user["id"]
            session["username"]  = user["username"]
            session["role"]      = user["role"]
            session["name"]      = user["name"]
            session["doctor_id"] = user.get("doctor_id")
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password. Please try again.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        name     = request.form.get("name", "").strip()
        phone    = request.form.get("phone", "").strip()

        if not username or not password or not name or not phone:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        user, err = Auth.register_user(username, password, name, phone)
        if err:
            flash(err, "danger")
        else:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

# ─── Patient routes ───────────────────────────────────────────────────────────

@app.route("/patient")
@Auth.login_required
@Auth.role_required("PATIENT")
def patient_dashboard():
    # Find bookings matching this session user's name
    my_bookings = [p for p in qm.patients if p["name"] == session.get("name")]
    return render_template("patient_dashboard.html",
                           doctors=qm.doctors,
                           my_bookings=my_bookings)

@app.route("/book", methods=["POST"])
@Auth.login_required
@Auth.role_required("PATIENT")
def book_appointment():
    name      = request.form.get("name", "").strip()
    age       = request.form.get("age", "0").strip()
    phone     = request.form.get("phone", "").strip()
    symptoms  = request.form.get("symptoms", "").strip()
    doctor_id = request.form.get("doctor_id", "1").strip()
    appt_time = request.form.get("appt_time", "").strip()

    if not name or not phone or not symptoms:
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for("patient_dashboard"))

    # Add patient to queue
    p = qm.add_patient(name, age, phone, symptoms, doctor_id, appt_time)

    # AI triage — check symptoms for HIGH priority
    t = triage.assess_priority(symptoms=symptoms)
    if t["priority"] == "HIGH":
        p["priority"] = "HIGH"
        qm._rebuild_positions()

    # Send SMS notification to patient
    sms.notify_booked(
        phone  = phone,
        name   = name,
        token  = p["token"],
        doctor = p["doctor_name"],
        wait   = p["estimated_wait"]
    )

    # Text-to-speech announcement
    vm.announce_token(p["token"], p["doctor_name"])

    flash(
        f"Appointment booked successfully! "
        f"Your Token is #{p['token']}. "
        f"Estimated wait: {p['estimated_wait']} min. "
        f"SMS sent to {phone}.",
        "success"
    )
    return redirect(url_for("patient_dashboard"))

# ─── Doctor routes ────────────────────────────────────────────────────────────

@app.route("/doctor")
@Auth.login_required
@Auth.role_required("DOCTOR")
def doctor_dashboard():
    doc_id      = session.get("doctor_id")
    my_patients = []

    if doc_id:
        my_patients = [
            p for p in qm.queue
            if p.get("doctor_id") == doc_id and p["status"] != "completed"
        ]
    else:
        my_patients = [
            p for p in qm.queue
            if p["status"] != "completed"
        ]

    return render_template("doctor_dashboard.html",
                           patients=my_patients,
                           doctor_name=session.get("name", "Doctor"))

@app.route("/doctor/complete/<int:token>", methods=["POST"])
@Auth.login_required
@Auth.role_required("DOCTOR")
def complete_patient(token):
    done = qm.complete_patient(token)
    if done:
        nxt = qm.get_active()
        if nxt:
            # Send SMS to next patient — their turn has arrived
            sms.notify_ready(
                phone  = nxt["phone"],
                name   = nxt["name"],
                token  = nxt["token"],
                doctor = nxt["doctor_name"],
                room   = nxt["doctor_room"]
            )
            # Also notify patient who is 2nd in line
            waiting = [p for p in qm.queue if p["status"] == "waiting"]
            if len(waiting) >= 1:
                upcoming = waiting[0]
                sms.notify_approaching(
                    phone = upcoming["phone"],
                    name  = upcoming["name"],
                    token = upcoming["token"]
                )
            # TTS announcement
            vm.announce_token(nxt["token"], nxt["doctor_name"])

        flash("Patient marked as complete. Next patient has been notified via SMS.", "success")
    else:
        flash("Could not complete — token not found or patient is not active.", "warning")

    return redirect(url_for("doctor_dashboard"))

# ─── Admin routes ─────────────────────────────────────────────────────────────

@app.route("/admin")
@Auth.login_required
@Auth.role_required("ADMIN")
def admin_dashboard():
    return render_template("admin_dashboard.html",
                           stats=qm.get_stats(),
                           sms_log=sms.get_log())

# ─── Live queue display ───────────────────────────────────────────────────────

@app.route("/display")
def queue_display():
    return render_template("queue_display.html")

# ─── IoT data endpoint ────────────────────────────────────────────────────────

@app.route("/iot-data", methods=["POST"])
def iot_data():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"status": "error", "message": "No JSON received"}), 400
    result = qm.update_iot(data)
    return jsonify({"status": "ok", "stored": result}), 200

# ─── JSON API endpoints ───────────────────────────────────────────────────────

@app.route("/api/queue")
def api_queue():
    return jsonify(qm.get_queue())

@app.route("/api/patients")
def api_patients():
    return jsonify(qm.patients)

@app.route("/api/iot-data")
def api_iot():
    return jsonify(qm.iot_data)

@app.route("/api/stats")
def api_stats():
    return jsonify(qm.get_stats())

@app.route("/api/active")
def api_active():
    return jsonify({
        "active":        qm.get_active(),
        "next":          qm.get_next(),
        "waiting_count": len([p for p in qm.queue if p["status"] == "waiting"]),
    })

@app.route("/api/export")
def api_export():
    return jsonify(qm.export_all())

@app.route("/api/sms-log")
def api_sms():
    return jsonify(sms.get_log())

# ─── Seed demo data ───────────────────────────────────────────────────────────

def seed_demo():
    # Add demo patients
    qm.add_patient("Rahul Verma",   34, "9876543210", "Fever and headache",   1, "10:00")
    qm.add_patient("Anjali Singh",  28, "9123456789", "Chest pain",           2, "10:15")
    qm.add_patient("Mohit Kumar",   45, "9988776655", "Back pain",            1, "10:30")
    qm.add_patient("Sneha Patil",   22, "9000001111", "Cold and cough",       3, "10:45")
    qm.add_patient("Demo Patient",  30, "9999999999", "General checkup",      1, "11:00")

    # Mark Anjali as HIGH priority (chest pain)
    for p in qm.patients:
        if "Chest" in p["symptoms"] or "chest" in p["symptoms"]:
            p["priority"] = "HIGH"

    # Seed IoT sensor data
    qm.update_iot({
        "temperature":        28.4,
        "humidity":           55.0,
        "motion_detected":    True,
        "waiting_room_count": 12,
    })

    print("✅ Demo data seeded — 5 patients added.")
    print(f"   Active patient: {qm.get_active()['name'] if qm.get_active() else 'None'}")

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    seed_demo()
    print("\n🏥  Smart Hospital Queue System")
    print("   ► http://localhost:5000")
    print("\n   Credentials:")
    print("   admin   / admin123   → Admin Dashboard")
    print("   doctor1 / doctor123  → Doctor Dashboard")
    print("   patient / pass123    → Patient Portal")
    print("\n   Extra URLs:")
    print("   /display             → Live TV Queue Screen")
    print("   /api/export          → Full JSON Export")
    print("   /api/queue           → Live Queue JSON\n")
    app.run(debug=True, port=5000)