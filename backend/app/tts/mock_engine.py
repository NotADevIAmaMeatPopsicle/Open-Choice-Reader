import hashlib
import math
import wave
from pathlib import Path

from app.tts.base import TTSEngine


class MockEngine(TTSEngine):
    name = "mock"

    def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sample_rate = 16_000
        duration_seconds = max(0.15, min(len(text) * 0.01, 1.0))
        frame_count = max(1, int(sample_rate * duration_seconds))
        frequency = 220 + (int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:4], 16) % 200)
        amplitude = 10_000

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for index in range(frame_count):
                sample = int(
                    amplitude * math.sin((2 * math.pi * frequency * index) / sample_rate)
                )
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))

            wav_file.writeframes(bytes(frames))

        return output_path
