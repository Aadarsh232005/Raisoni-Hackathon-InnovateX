import requests
from datetime import datetime

# ─────────────────────────────────────────────
#  PASTE YOUR FAST2SMS API KEY HERE
# ─────────────────────────────────────────────
FAST2SMS_API_KEY = "FqkPwDSuA8TzMRicBZ642Hfmrtbv0KCn71WyhlxgXeG39aJ5IjfH3wUYNEld2oGQbR0rJyviMXnugAmV"

# Set to False when you want REAL SMS to be sent
DEMO_MODE = False
# ─────────────────────────────────────────────

sms_log = []

def _send(phone, message):
    """Send real SMS via Fast2SMS or log in demo mode."""

    entry = {
        "phone":   str(phone),
        "message": message,
        "time":    datetime.now().strftime("%H:%M:%S"),
        "status":  "PENDING",
    }

    if DEMO_MODE or FAST2SMS_API_KEY == "PASTE_YOUR_API_KEY_HERE":
        entry["status"] = "DEMO (not sent)"
        sms_log.append(entry)
        print(f"[SMS DEMO] To: {phone} | {message}")
        return entry

    # Real Fast2SMS API call
    try:
        url = "https://www.fast2sms.com/dev/bulkV2"

        headers = {
            "authorization": FAST2SMS_API_KEY,
            "Content-Type":  "application/json",
        }

        payload = {
            "route":    "q",          # Transactional route
            "message":  message,
            "language": "english",
            "flash":    0,
            "numbers":  str(phone),   # 10-digit Indian mobile number
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result   = response.json()

        if result.get("return") is True:
            entry["status"] = "SENT ✓"
            print(f"[SMS SENT] To: {phone} | {message}")
        else:
            entry["status"] = f"FAILED: {result.get('message', 'Unknown error')}"
            print(f"[SMS FAILED] {result}")

    except requests.exceptions.Timeout:
        entry["status"] = "FAILED: Timeout"
        print(f"[SMS ERROR] Timeout sending to {phone}")

    except requests.exceptions.ConnectionError:
        entry["status"] = "FAILED: No internet"
        print(f"[SMS ERROR] No internet connection")

    except Exception as e:
        entry["status"] = f"FAILED: {str(e)}"
        print(f"[SMS ERROR] {e}")

    sms_log.append(entry)
    return entry


def notify_booked(phone, name, token, doctor, wait):
    msg = (
        f"Hi {name}! Your token #{token} is confirmed. "
        f"Doctor: {doctor}. Est. wait: {wait} mins. "
        f"- SmartHospital"
    )
    return _send(phone, msg)


def notify_approaching(phone, name, token):
    msg = (
        f"Dear {name}, your turn is approaching! "
        f"Token #{token}. Please be ready. "
        f"- SmartHospital"
    )
    return _send(phone, msg)


def notify_ready(phone, name, token, doctor, room):
    msg = (
        f"Token #{token} {name}, please proceed to "
        f"{doctor} at {room} NOW. "
        f"- SmartHospital"
    )
    return _send(phone, msg)


def get_log():
    return sms_log