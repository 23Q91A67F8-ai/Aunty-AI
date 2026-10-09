import pyttsx3
from typing import Optional
from PySide6.QtCore import QThread, Signal


class TextToSpeechEngine:
    """Handles text-to-speech conversion."""

    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)  # Speech speed
        self.engine.setProperty('volume', 0.9)  # Volume (0-1)

    def speak(self, text: str):
        """Speak the given text."""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")

    def set_rate(self, rate: int):
        """Set speech rate (50-300, default 150)."""
        self.engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        """Set volume (0-1)."""
        self.engine.setProperty('volume', max(0, min(1, volume)))

    def stop(self):
        """Stop speaking."""
        try:
            self.engine.stop()
        except Exception as e:
            print(f"TTS Stop Error: {e}")


class SpeechWorker(QThread):
    """Worker thread for TTS to avoid blocking UI."""
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, text: str, rate: int = 150):
        super().__init__()
        self.text = text
        self.rate = rate
        self.tts = TextToSpeechEngine()
        self.tts.set_rate(rate)

    def run(self):
        try:
            self.tts.speak(self.text)
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))
