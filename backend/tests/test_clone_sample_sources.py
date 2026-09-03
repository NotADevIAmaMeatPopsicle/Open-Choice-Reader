from importlib import import_module, reload


def test_search_librivox_samples_returns_provenance_candidates(monkeypatch):
    module = reload(import_module("app.services.clone_sample_sources"))

    def fake_get_json(url: str, params: dict[str, object]):
        if "audiobooks" in url:
            return {
                "books": [
                    {
                        "id": "123",
                        "title": "Public Domain Reading",
                        "authors": [{"first_name": "Ada", "last_name": "Reader"}],
                        "url_text_source": "https://www.gutenberg.org/ebooks/123",
                        "url_librivox": "https://librivox.org/public-domain-reading/",
                    }
                ]
            }
        return {
            "sections": [
                {
                    "id": "999",
                    "title": "Chapter 1",
                    "playtime": "00:04:12",
                    "listen_url": "https://archive.org/download/sample/chapter1.mp3",
                }
            ]
        }

    monkeypatch.setattr(module, "_get_json", fake_get_json)

    candidates = module.search_clone_sample_candidates("public domain", limit=1)

    assert len(candidates) == 1
    assert candidates[0].provider == "librivox"
    assert candidates[0].title == "Public Domain Reading - Chapter 1"
    assert candidates[0].speaker == "Ada Reader"
    assert candidates[0].audio_url == "https://archive.org/download/sample/chapter1.mp3"
    assert candidates[0].transcript_source_url == "https://www.gutenberg.org/ebooks/123"
    assert candidates[0].license_label == "Public domain or LibriVox-provided public-domain recording"
    assert candidates[0].is_importable is True
