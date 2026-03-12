import os

def text_to_speech(text, filename="announce.mp3"):
    try:
        from gtts import gTTS
        path = os.path.join("static", filename)
        gTTS(text=text, lang="en").save(path)
        return path
    except Exception as e:
        print(f"[TTS] {e}")
        return None

def announce_token(token, doctor_name):
    msg = f"Token number {token}. Please proceed to {doctor_name}. Thank you."
    return text_to_speech(msg, f"token_{token}.mp3")