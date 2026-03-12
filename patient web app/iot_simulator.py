"""
Run separately: python iot_simulator.py
Simulates ESP32 sending sensor data every 4 seconds.
"""
import requests, random, time, json

URL = "http://localhost:5000/iot-data"

def random_payload():
    return {
        "temperature":        round(random.uniform(24, 32), 1),
        "humidity":           round(random.uniform(40, 70), 1),
        "motion_detected":    random.choice([True, True, False]),
        "waiting_room_count": random.randint(5, 25),
        "patient_id":         None,
    }

print("🏥  ESP32 IoT Simulator started — sending every 4 seconds...")
print(f"   Target: {URL}\n")

while True:
    payload = random_payload()
    try:
        r = requests.post(URL, json=payload, timeout=3)
        print(f"[{time.strftime('%H:%M:%S')}] Sent: {json.dumps(payload)}  → {r.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ Server not reachable. Is app.py running?")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
    time.sleep(4)