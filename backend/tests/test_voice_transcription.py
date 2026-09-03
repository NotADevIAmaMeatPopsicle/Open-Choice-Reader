from io import BytesIO
from importlib import import_module, reload
from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers, UploadFile


def test_transcribe_reference_audio_uses_local_whisper_model(monkeypatch: pytest.MonkeyPatch) -> None:
    module = reload(import_module("app.services.voice_transcription"))

    class FakeSegment:
        start = 0.0
        end = 1.25
        text = " Alice reads into his own microphone. "

    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            self.model_name = model_name
            self.device = device
            self.compute_type = compute_type

        def transcribe(self, audio_path: str, *, beam_size: int):
            assert audio_path.endswith(".wav")
            assert beam_size == 5
            return [FakeSegment()], SimpleNamespace(language="en")

    monkeypatch.setattr(module, "import_module", lambda name: SimpleNamespace(WhisperModel=FakeWhisperModel))

    upload = UploadFile(
        file=BytesIO(b"RIFFvoice"),
        filename="voice.wav",
        headers=Headers({"content-type": "audio/wav"}),
    )

    result = module.transcribe_reference_audio(reference_audio=upload)

    assert result.transcript == "Alice reads into his own microphone."
    assert result.language == "en"
    assert result.engine.startswith("faster-whisper:")
    assert result.segments[0].text == "Alice reads into his own microphone."


def test_transcribe_reference_audio_rejects_empty_file() -> None:
    module = reload(import_module("app.services.voice_transcription"))
    upload = UploadFile(
        file=BytesIO(b""),
        filename="voice.wav",
        headers=Headers({"content-type": "audio/wav"}),
    )

    with pytest.raises(ValueError, match="reference audio is empty"):
        module.transcribe_reference_audio(reference_audio=upload)
