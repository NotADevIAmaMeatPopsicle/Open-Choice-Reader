import sys
from importlib import import_module

from sqlalchemy.orm import DeclarativeBase


if "Base" not in globals():
    class Base(DeclarativeBase):
        pass


_MODEL_MODULES = (
    "app.models.app_setting",
    "app.models.auth_session",
    "app.models.collection",
    "app.models.document",
    "app.models.document_profile",
    "app.models.document_progress",
    "app.models.friendship",
    "app.models.job",
    "app.models.playback_session",
    "app.models.section",
    "app.models.shared_item",
    "app.models.text_chunk",
    "app.models.theme_profile",
    "app.models.user",
    "app.models.user_invite",
    "app.models.user_setting",
    "app.models.voice_preset",
)

_CLASS_EXPORTS = {
    "AppSetting": "app.models.app_setting",
    "AuthSession": "app.models.auth_session",
    "Collection": "app.models.collection",
    "CollectionDocument": "app.models.collection",
    "Document": "app.models.document",
    "DocumentProfile": "app.models.document_profile",
    "DocumentProgress": "app.models.document_progress",
    "Friendship": "app.models.friendship",
    "Job": "app.models.job",
    "PlaybackSession": "app.models.playback_session",
    "Section": "app.models.section",
    "SharedItem": "app.models.shared_item",
    "TextChunk": "app.models.text_chunk",
    "ThemeProfile": "app.models.theme_profile",
    "User": "app.models.user",
    "UserInvite": "app.models.user_invite",
    "UserSetting": "app.models.user_setting",
    "VoicePreset": "app.models.voice_preset",
}


for module_name in _MODEL_MODULES:
    if module_name not in sys.modules:
        import_module(module_name)


def __getattr__(name: str):
    module_name = _CLASS_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


__all__ = ["Base", *_CLASS_EXPORTS.keys()]
