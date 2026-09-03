from dataclasses import dataclass
import json
import re
from typing import TYPE_CHECKING

from sqlalchemy import select

from app import db

if TYPE_CHECKING:
    from app.models.theme_profile import ThemeProfile


DEFAULT_THEME_ID = "ember"


def _theme_profile_model():
    from app.models.theme_profile import ThemeProfile

    return ThemeProfile


@dataclass(frozen=True)
class ThemeSnapshot:
    id: str
    name: str
    description: str | None
    source_kind: str
    source_label: str
    source_reference: str | None
    is_builtin: bool
    sort_order: int
    family: str
    preview_variant: str
    background_asset_path: str | None
    background_overlay_path: str | None
    shelf_asset_path: str | None
    surface_texture_asset_path: str | None
    supports_mix_and_match: bool
    tokens: dict[str, str]


BUILTIN_THEME_SEEDS: tuple[dict[str, object], ...] = (
    {
        "id": "ember",
        "name": "Ember",
        "description": "Warm shelves, amber highlights, and the original house look.",
        "source_kind": "house",
        "source_label": "Open Choice Reader",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 10,
        "tokens": {
            "--color-bg": "#151413",
            "--color-bg-elevated": "#1b1918",
            "--color-panel": "rgba(25, 24, 23, 0.94)",
            "--color-panel-strong": "#23201e",
            "--color-panel-soft": "rgba(39, 34, 31, 0.86)",
            "--color-text": "#f7f2ea",
            "--color-text-muted": "#c7b7a2",
            "--color-border": "rgba(236, 213, 182, 0.12)",
            "--color-accent": "#d7a24c",
            "--color-accent-strong": "#9b6b23",
            "--color-danger": "#ffb4ab",
            "--color-success": "#7dd3a5",
            "--color-shadow": "rgba(0, 0, 0, 0.32)",
            "--color-shelf-dark": "#2b1f16",
            "--color-shelf-light": "#4d3525",
            "--theme-glow-left": "rgba(215, 162, 76, 0.18)",
            "--theme-glow-right": "rgba(116, 74, 38, 0.34)",
        },
    },
    {
        "id": "ocean",
        "name": "Ocean",
        "description": "Cool blue shelving with a brighter media-center accent palette.",
        "source_kind": "house",
        "source_label": "Open Choice Reader",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 20,
        "tokens": {
            "--color-bg": "#10171c",
            "--color-bg-elevated": "#172229",
            "--color-panel": "rgba(18, 28, 34, 0.94)",
            "--color-panel-strong": "#21313a",
            "--color-panel-soft": "rgba(27, 44, 52, 0.86)",
            "--color-text": "#eef7fb",
            "--color-text-muted": "#b6ccd6",
            "--color-border": "rgba(162, 202, 222, 0.16)",
            "--color-accent": "#5bc0d1",
            "--color-accent-strong": "#2a7f95",
            "--color-danger": "#ffb4ab",
            "--color-success": "#7dd3a5",
            "--color-shadow": "rgba(0, 0, 0, 0.32)",
            "--color-shelf-dark": "#18303d",
            "--color-shelf-light": "#294e5b",
            "--theme-glow-left": "rgba(91, 192, 209, 0.18)",
            "--theme-glow-right": "rgba(41, 78, 91, 0.32)",
        },
    },
    {
        "id": "forest",
        "name": "Forest",
        "description": "Deep green shelves with a softer natural accent range.",
        "source_kind": "house",
        "source_label": "Open Choice Reader",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 30,
        "tokens": {
            "--color-bg": "#131814",
            "--color-bg-elevated": "#1a211b",
            "--color-panel": "rgba(23, 30, 24, 0.95)",
            "--color-panel-strong": "#283329",
            "--color-panel-soft": "rgba(33, 44, 34, 0.86)",
            "--color-text": "#f4f7ef",
            "--color-text-muted": "#c4d1c0",
            "--color-border": "rgba(181, 212, 164, 0.14)",
            "--color-accent": "#93c572",
            "--color-accent-strong": "#557b3f",
            "--color-danger": "#ffb4ab",
            "--color-success": "#7dd3a5",
            "--color-shadow": "rgba(0, 0, 0, 0.32)",
            "--color-shelf-dark": "#23311f",
            "--color-shelf-light": "#42583a",
            "--theme-glow-left": "rgba(147, 197, 114, 0.15)",
            "--theme-glow-right": "rgba(66, 88, 58, 0.30)",
        },
    },
    {
        "id": "midnight-ink",
        "name": "Midnight Ink",
        "description": "Reading-focused contrast with ink-blue panels and a clean cyan cue.",
        "source_kind": "inspired",
        "source_label": "Reading-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 40,
        "family": "reader_focused",
        "tokens": {
            "--color-bg": "#0f1319",
            "--color-bg-elevated": "#151b24",
            "--color-panel": "rgba(18, 23, 31, 0.94)",
            "--color-panel-strong": "#1d2733",
            "--color-panel-soft": "rgba(28, 37, 49, 0.86)",
            "--color-text": "#edf4fb",
            "--color-text-muted": "#aabccf",
            "--color-border": "rgba(142, 185, 230, 0.14)",
            "--color-accent": "#72b7ff",
            "--color-accent-strong": "#3a79b4",
            "--color-danger": "#ffb4ab",
            "--color-success": "#7dd3a5",
            "--color-shadow": "rgba(0, 0, 0, 0.34)",
            "--color-shelf-dark": "#14202b",
            "--color-shelf-light": "#274152",
            "--theme-glow-left": "rgba(114, 183, 255, 0.18)",
            "--theme-glow-right": "rgba(58, 121, 180, 0.28)",
        },
    },
    {
        "id": "linen-copper",
        "name": "Linen Copper",
        "description": "A warm reading palette with copper trim and softer shelves.",
        "source_kind": "inspired",
        "source_label": "Reading-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 50,
        "family": "reader_focused",
        "tokens": {
            "--color-bg": "#171310",
            "--color-bg-elevated": "#1f1915",
            "--color-panel": "rgba(29, 24, 20, 0.94)",
            "--color-panel-strong": "#34271f",
            "--color-panel-soft": "rgba(46, 37, 31, 0.86)",
            "--color-text": "#f5eee5",
            "--color-text-muted": "#d0bba7",
            "--color-border": "rgba(223, 173, 120, 0.15)",
            "--color-accent": "#d99555",
            "--color-accent-strong": "#9f6030",
            "--color-danger": "#ffb4ab",
            "--color-success": "#88d3a0",
            "--color-shadow": "rgba(0, 0, 0, 0.33)",
            "--color-shelf-dark": "#2d1f16",
            "--color-shelf-light": "#5a3c29",
            "--theme-glow-left": "rgba(217, 149, 85, 0.15)",
            "--theme-glow-right": "rgba(106, 68, 40, 0.30)",
        },
    },
    {
        "id": "slate-orchid",
        "name": "Slate Orchid",
        "description": "Cool slate shelves with a restrained orchid signal color.",
        "source_kind": "inspired",
        "source_label": "Reading-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 60,
        "family": "reader_focused",
        "tokens": {
            "--color-bg": "#13131a",
            "--color-bg-elevated": "#1b1b24",
            "--color-panel": "rgba(25, 25, 34, 0.95)",
            "--color-panel-strong": "#2d2b3a",
            "--color-panel-soft": "rgba(40, 38, 53, 0.86)",
            "--color-text": "#f3f0fb",
            "--color-text-muted": "#bbb2d1",
            "--color-border": "rgba(196, 170, 233, 0.14)",
            "--color-accent": "#b889f0",
            "--color-accent-strong": "#7f55b6",
            "--color-danger": "#ffb4ab",
            "--color-success": "#7fd6b8",
            "--color-shadow": "rgba(0, 0, 0, 0.34)",
            "--color-shelf-dark": "#211b2d",
            "--color-shelf-light": "#3c3250",
            "--theme-glow-left": "rgba(184, 137, 240, 0.16)",
            "--theme-glow-right": "rgba(88, 66, 127, 0.28)",
        },
    },
    {
        "id": "projector-noir",
        "name": "Projector Noir",
        "description": "Cinema darkness with cool projection glow and glassy panels.",
        "source_kind": "inspired",
        "source_label": "Cinema-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 70,
        "family": "cinema_focused",
        "tokens": {
            "--color-bg": "#090d16",
            "--color-bg-elevated": "#101726",
            "--color-panel": "rgba(13, 18, 29, 0.95)",
            "--color-panel-strong": "#172338",
            "--color-panel-soft": "rgba(21, 31, 49, 0.88)",
            "--color-text": "#f3f7fc",
            "--color-text-muted": "#aec0d7",
            "--color-border": "rgba(120, 208, 255, 0.16)",
            "--color-accent": "#66d4ff",
            "--color-accent-strong": "#2c84a7",
            "--color-danger": "#ff9c9c",
            "--color-success": "#85dbad",
            "--color-shadow": "rgba(0, 0, 0, 0.38)",
            "--color-shelf-dark": "#102030",
            "--color-shelf-light": "#18354e",
            "--theme-glow-left": "rgba(102, 212, 255, 0.18)",
            "--theme-glow-right": "rgba(44, 132, 167, 0.34)",
        },
    },
    {
        "id": "ruby-marquee",
        "name": "Ruby Marquee",
        "description": "A red velvet palette with brighter marquee accents.",
        "source_kind": "inspired",
        "source_label": "Cinema-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 80,
        "family": "cinema_focused",
        "tokens": {
            "--color-bg": "#130b10",
            "--color-bg-elevated": "#1d1119",
            "--color-panel": "rgba(28, 16, 25, 0.95)",
            "--color-panel-strong": "#3a1525",
            "--color-panel-soft": "rgba(50, 20, 34, 0.88)",
            "--color-text": "#fbf1f5",
            "--color-text-muted": "#d9b8c4",
            "--color-border": "rgba(255, 120, 148, 0.15)",
            "--color-accent": "#ff6f92",
            "--color-accent-strong": "#b23959",
            "--color-danger": "#ffc0b6",
            "--color-success": "#7ed7ad",
            "--color-shadow": "rgba(0, 0, 0, 0.38)",
            "--color-shelf-dark": "#2b121c",
            "--color-shelf-light": "#5c2234",
            "--theme-glow-left": "rgba(255, 111, 146, 0.16)",
            "--theme-glow-right": "rgba(178, 57, 89, 0.32)",
        },
    },
    {
        "id": "frost-reel",
        "name": "Frost Reel",
        "description": "A steel-blue media-center palette with icy contrast.",
        "source_kind": "inspired",
        "source_label": "Cinema-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 90,
        "family": "cinema_focused",
        "tokens": {
            "--color-bg": "#0d1115",
            "--color-bg-elevated": "#141c22",
            "--color-panel": "rgba(18, 26, 32, 0.95)",
            "--color-panel-strong": "#243440",
            "--color-panel-soft": "rgba(30, 44, 54, 0.87)",
            "--color-text": "#eef6fb",
            "--color-text-muted": "#b7c9d5",
            "--color-border": "rgba(168, 210, 230, 0.15)",
            "--color-accent": "#8ed6ee",
            "--color-accent-strong": "#4e90aa",
            "--color-danger": "#ffb4ab",
            "--color-success": "#8dd8b1",
            "--color-shadow": "rgba(0, 0, 0, 0.38)",
            "--color-shelf-dark": "#1a2b34",
            "--color-shelf-light": "#35515f",
            "--theme-glow-left": "rgba(142, 214, 238, 0.16)",
            "--theme-glow-right": "rgba(78, 144, 170, 0.30)",
        },
    },
    {
        "id": "signal-mint",
        "name": "Signal Mint",
        "description": "Mint contrast with a clean player-app silhouette.",
        "source_kind": "inspired",
        "source_label": "Player-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 100,
        "family": "player_focused",
        "tokens": {
            "--color-bg": "#111517",
            "--color-bg-elevated": "#171d20",
            "--color-panel": "rgba(18, 24, 27, 0.94)",
            "--color-panel-strong": "#243034",
            "--color-panel-soft": "rgba(30, 39, 43, 0.86)",
            "--color-text": "#eff8f4",
            "--color-text-muted": "#b4c9c0",
            "--color-border": "rgba(117, 218, 185, 0.14)",
            "--color-accent": "#5fd7b3",
            "--color-accent-strong": "#29916f",
            "--color-danger": "#ffb4ab",
            "--color-success": "#8be4bc",
            "--color-shadow": "rgba(0, 0, 0, 0.30)",
            "--color-shelf-dark": "#1f2d2b",
            "--color-shelf-light": "#33504b",
            "--theme-glow-left": "rgba(95, 215, 179, 0.15)",
            "--theme-glow-right": "rgba(41, 145, 111, 0.28)",
        },
    },
    {
        "id": "sunset-cassette",
        "name": "Sunset Cassette",
        "description": "Coral energy with warmer player chrome and readable shelves.",
        "source_kind": "inspired",
        "source_label": "Player-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 110,
        "family": "player_focused",
        "tokens": {
            "--color-bg": "#171112",
            "--color-bg-elevated": "#211617",
            "--color-panel": "rgba(30, 20, 22, 0.94)",
            "--color-panel-strong": "#3d2324",
            "--color-panel-soft": "rgba(50, 31, 33, 0.86)",
            "--color-text": "#fbf2ef",
            "--color-text-muted": "#d4b8b1",
            "--color-border": "rgba(255, 156, 122, 0.14)",
            "--color-accent": "#ff8b61",
            "--color-accent-strong": "#b45639",
            "--color-danger": "#ffb4ab",
            "--color-success": "#86d1a8",
            "--color-shadow": "rgba(0, 0, 0, 0.31)",
            "--color-shelf-dark": "#32201d",
            "--color-shelf-light": "#5a382d",
            "--theme-glow-left": "rgba(255, 139, 97, 0.15)",
            "--theme-glow-right": "rgba(180, 86, 57, 0.28)",
        },
    },
    {
        "id": "deep-frequency",
        "name": "Deep Frequency",
        "description": "An indigo night palette with crisp violet signal accents.",
        "source_kind": "inspired",
        "source_label": "Player-focused",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 120,
        "family": "player_focused",
        "tokens": {
            "--color-bg": "#10111a",
            "--color-bg-elevated": "#161926",
            "--color-panel": "rgba(19, 22, 34, 0.95)",
            "--color-panel-strong": "#252a42",
            "--color-panel-soft": "rgba(34, 39, 60, 0.86)",
            "--color-text": "#f0f2fb",
            "--color-text-muted": "#b7bdd8",
            "--color-border": "rgba(155, 144, 255, 0.15)",
            "--color-accent": "#8f86ff",
            "--color-accent-strong": "#534db0",
            "--color-danger": "#ffb4ab",
            "--color-success": "#87d7c1",
            "--color-shadow": "rgba(0, 0, 0, 0.33)",
            "--color-shelf-dark": "#1f2440",
            "--color-shelf-light": "#353e66",
            "--theme-glow-left": "rgba(143, 134, 255, 0.16)",
            "--theme-glow-right": "rgba(83, 77, 176, 0.28)",
        },
    },
    {
        "id": "sunlit-reading-room",
        "name": "Sunlit Reading Room",
        "description": "A bright reading-room treatment with cream paper, pale oak shelving, and a calmer daytime glow.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 130,
        "family": "showcase",
        "preview_variant": "light-airy",
        "background_asset_path": "/theme-assets/backgrounds/sunlit-reading-room.svg",
        "background_overlay_path": "/theme-assets/textures/paper-glow-light.svg",
        "shelf_asset_path": "/theme-assets/shelves/sunlit-oak-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/parchment-soft.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#f3ead7",
            "--color-bg-elevated": "#fdf8ef",
            "--color-panel": "rgba(255, 249, 241, 0.96)",
            "--color-panel-strong": "#fff9ef",
            "--color-panel-soft": "rgba(244, 233, 214, 0.94)",
            "--color-text": "#32261d",
            "--color-text-muted": "#705b48",
            "--color-border": "rgba(156, 124, 88, 0.22)",
            "--color-accent": "#bf8640",
            "--color-accent-strong": "#8d5820",
            "--color-danger": "#b95656",
            "--color-success": "#3f7d57",
            "--color-shadow": "rgba(101, 77, 53, 0.18)",
            "--color-shelf-dark": "#8f6342",
            "--color-shelf-light": "#c9a27a",
            "--theme-glow-left": "rgba(255, 218, 163, 0.4)",
            "--theme-glow-right": "rgba(236, 217, 180, 0.46)",
        },
    },
    {
        "id": "linen-ledger",
        "name": "Linen Ledger",
        "description": "Editorial cream panels, pale ledger lines, and a softer bookstore shelf treatment.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 140,
        "family": "showcase",
        "preview_variant": "light-airy",
        "background_asset_path": "/theme-assets/backgrounds/linen-ledger.svg",
        "background_overlay_path": "/theme-assets/textures/linen-weave.svg",
        "shelf_asset_path": "/theme-assets/shelves/painted-cream-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/linen-weave.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#f2ece1",
            "--color-bg-elevated": "#fcf8f1",
            "--color-panel": "rgba(253, 248, 241, 0.96)",
            "--color-panel-strong": "#fffaf4",
            "--color-panel-soft": "rgba(240, 231, 218, 0.93)",
            "--color-text": "#302820",
            "--color-text-muted": "#6f6153",
            "--color-border": "rgba(132, 107, 82, 0.2)",
            "--color-accent": "#bf7251",
            "--color-accent-strong": "#8e4e30",
            "--color-danger": "#b85d57",
            "--color-success": "#4f7d60",
            "--color-shadow": "rgba(89, 73, 58, 0.17)",
            "--color-shelf-dark": "#825c44",
            "--color-shelf-light": "#be9676",
            "--theme-glow-left": "rgba(243, 210, 177, 0.3)",
            "--theme-glow-right": "rgba(237, 231, 214, 0.46)",
        },
    },
    {
        "id": "sea-glass-study",
        "name": "Sea Glass Study",
        "description": "A bright coastal study with washed teal accents, airy paper surfaces, and brighter shelf contrast.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 150,
        "family": "showcase",
        "preview_variant": "light-airy",
        "background_asset_path": "/theme-assets/backgrounds/sea-glass-study.svg",
        "background_overlay_path": "/theme-assets/textures/sea-mist-overlay.svg",
        "shelf_asset_path": "/theme-assets/shelves/weathered-teak-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/linen-weave.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#e5f0ee",
            "--color-bg-elevated": "#f7fcfb",
            "--color-panel": "rgba(249, 254, 252, 0.96)",
            "--color-panel-strong": "#ffffff",
            "--color-panel-soft": "rgba(224, 239, 236, 0.93)",
            "--color-text": "#203234",
            "--color-text-muted": "#527074",
            "--color-border": "rgba(74, 122, 123, 0.2)",
            "--color-accent": "#4a9fa8",
            "--color-accent-strong": "#2e6c75",
            "--color-danger": "#b55b63",
            "--color-success": "#3f8869",
            "--color-shadow": "rgba(63, 93, 96, 0.17)",
            "--color-shelf-dark": "#4f6d6c",
            "--color-shelf-light": "#9bc8c3",
            "--theme-glow-left": "rgba(177, 230, 223, 0.3)",
            "--theme-glow-right": "rgba(211, 241, 236, 0.44)",
        },
    },
    {
        "id": "garden-atlas",
        "name": "Garden Atlas",
        "description": "Sage, cream, and sunlit conservatory warmth for readers who want a softer daytime shelf.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 160,
        "family": "showcase",
        "preview_variant": "light-airy",
        "background_asset_path": "/theme-assets/backgrounds/garden-atlas.svg",
        "background_overlay_path": "/theme-assets/textures/leaf-shadow-light.svg",
        "shelf_asset_path": "/theme-assets/shelves/sage-painted-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/parchment-soft.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#ebf1e2",
            "--color-bg-elevated": "#f8fbf1",
            "--color-panel": "rgba(251, 253, 246, 0.96)",
            "--color-panel-strong": "#ffffff",
            "--color-panel-soft": "rgba(233, 240, 223, 0.93)",
            "--color-text": "#293025",
            "--color-text-muted": "#5d6854",
            "--color-border": "rgba(111, 126, 98, 0.22)",
            "--color-accent": "#789760",
            "--color-accent-strong": "#58703f",
            "--color-danger": "#b45c55",
            "--color-success": "#417852",
            "--color-shadow": "rgba(88, 101, 76, 0.17)",
            "--color-shelf-dark": "#607553",
            "--color-shelf-light": "#abb98d",
            "--theme-glow-left": "rgba(188, 213, 163, 0.3)",
            "--theme-glow-right": "rgba(231, 241, 217, 0.44)",
        },
    },
    {
        "id": "mahogany-stacks",
        "name": "Mahogany Stacks",
        "description": "Classic dark-library warmth with walnut panels, brass glow, and deeper shelf definition.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 170,
        "family": "showcase",
        "preview_variant": "dark-cozy",
        "background_asset_path": "/theme-assets/backgrounds/mahogany-stacks.svg",
        "background_overlay_path": "/theme-assets/textures/warm-vignette.svg",
        "shelf_asset_path": "/theme-assets/shelves/mahogany-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/woodgrain-dark.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#16110e",
            "--color-bg-elevated": "#1b1411",
            "--color-panel": "rgba(31, 23, 19, 0.94)",
            "--color-panel-strong": "#3d2b24",
            "--color-panel-soft": "rgba(50, 35, 29, 0.9)",
            "--color-text": "#f6eee7",
            "--color-text-muted": "#d3bea9",
            "--color-border": "rgba(210, 167, 121, 0.2)",
            "--color-accent": "#d19657",
            "--color-accent-strong": "#8b5727",
            "--color-danger": "#ffb4ab",
            "--color-success": "#8bd1ab",
            "--color-shadow": "rgba(0, 0, 0, 0.34)",
            "--color-shelf-dark": "#382217",
            "--color-shelf-light": "#724530",
            "--theme-glow-left": "rgba(209, 150, 87, 0.2)",
            "--theme-glow-right": "rgba(121, 71, 48, 0.34)",
        },
    },
    {
        "id": "after-hours-atrium",
        "name": "After Hours Atrium",
        "description": "Cooler blue-black stacks, tall late-night library mood, and stronger media-room separation.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 180,
        "family": "showcase",
        "preview_variant": "dark-cozy",
        "background_asset_path": "/theme-assets/backgrounds/after-hours-atrium.svg",
        "background_overlay_path": "/theme-assets/textures/night-vignette.svg",
        "shelf_asset_path": "/theme-assets/shelves/atrium-night-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/slate-paper-dark.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#0d141c",
            "--color-bg-elevated": "#131d2a",
            "--color-panel": "rgba(17, 28, 40, 0.94)",
            "--color-panel-strong": "#23364c",
            "--color-panel-soft": "rgba(27, 42, 60, 0.9)",
            "--color-text": "#eff6fb",
            "--color-text-muted": "#b9cad8",
            "--color-border": "rgba(146, 182, 219, 0.18)",
            "--color-accent": "#7fb5eb",
            "--color-accent-strong": "#4a80ae",
            "--color-danger": "#ffb4ab",
            "--color-success": "#86d0b4",
            "--color-shadow": "rgba(0, 0, 0, 0.36)",
            "--color-shelf-dark": "#1b2c3f",
            "--color-shelf-light": "#35526f",
            "--theme-glow-left": "rgba(127, 181, 235, 0.18)",
            "--theme-glow-right": "rgba(46, 78, 113, 0.34)",
        },
    },
    {
        "id": "candlewick-catalog",
        "name": "Candlewick Catalog",
        "description": "Candlelit catalog room with amber paper glow, leather undertones, and shelf depth.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 190,
        "family": "showcase",
        "preview_variant": "dark-cozy",
        "background_asset_path": "/theme-assets/backgrounds/candlewick-catalog.svg",
        "background_overlay_path": "/theme-assets/textures/warm-vignette.svg",
        "shelf_asset_path": "/theme-assets/shelves/candlewick-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/leather-paper-dark.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#18110d",
            "--color-bg-elevated": "#221813",
            "--color-panel": "rgba(33, 24, 18, 0.94)",
            "--color-panel-strong": "#412d22",
            "--color-panel-soft": "rgba(53, 38, 29, 0.9)",
            "--color-text": "#f7f0e8",
            "--color-text-muted": "#d9c4af",
            "--color-border": "rgba(215, 177, 125, 0.2)",
            "--color-accent": "#e0ab61",
            "--color-accent-strong": "#94602e",
            "--color-danger": "#ffb4ab",
            "--color-success": "#93d4ac",
            "--color-shadow": "rgba(0, 0, 0, 0.35)",
            "--color-shelf-dark": "#362217",
            "--color-shelf-light": "#784735",
            "--theme-glow-left": "rgba(224, 171, 97, 0.22)",
            "--theme-glow-right": "rgba(126, 73, 48, 0.36)",
        },
    },
    {
        "id": "projector-noir-library",
        "name": "Projector Noir Library",
        "description": "A dark cinematic shelf room with projection light, glass chrome, and deeper contrast between surfaces.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 200,
        "family": "showcase",
        "preview_variant": "dark-cozy",
        "background_asset_path": "/theme-assets/backgrounds/projector-noir-library.svg",
        "background_overlay_path": "/theme-assets/textures/projection-beam.svg",
        "shelf_asset_path": "/theme-assets/shelves/noir-steel-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/slate-paper-dark.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#0a0f18",
            "--color-bg-elevated": "#0f1828",
            "--color-panel": "rgba(13, 22, 36, 0.95)",
            "--color-panel-strong": "#19314a",
            "--color-panel-soft": "rgba(20, 35, 57, 0.9)",
            "--color-text": "#f2f7fb",
            "--color-text-muted": "#b8cae1",
            "--color-border": "rgba(124, 196, 248, 0.22)",
            "--color-accent": "#66cbff",
            "--color-accent-strong": "#2b7fb5",
            "--color-danger": "#ffb4ab",
            "--color-success": "#84d7b1",
            "--color-shadow": "rgba(0, 0, 0, 0.4)",
            "--color-shelf-dark": "#132740",
            "--color-shelf-light": "#295279",
            "--theme-glow-left": "rgba(102, 203, 255, 0.22)",
            "--theme-glow-right": "rgba(37, 104, 158, 0.36)",
        },
    },
    {
        "id": "lantern-meadow-library",
        "name": "Lantern Meadow Library",
        "description": "A painted storybook library clearing with lantern glow, paper-soft clouds, and whimsical shelves.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 210,
        "family": "showcase",
        "preview_variant": "showpiece",
        "background_asset_path": "/theme-assets/backgrounds/lantern-meadow-library.svg",
        "background_overlay_path": "/theme-assets/textures/painted-paper.svg",
        "shelf_asset_path": "/theme-assets/shelves/storybook-painted-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/painted-paper.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#1a1b27",
            "--color-bg-elevated": "#252538",
            "--color-panel": "rgba(35, 36, 52, 0.9)",
            "--color-panel-strong": "#453c5b",
            "--color-panel-soft": "rgba(63, 60, 88, 0.86)",
            "--color-text": "#f8f1e7",
            "--color-text-muted": "#e3d2bf",
            "--color-border": "rgba(235, 194, 126, 0.22)",
            "--color-accent": "#efba72",
            "--color-accent-strong": "#aa7037",
            "--color-danger": "#ffbdb5",
            "--color-success": "#99d6a7",
            "--color-shadow": "rgba(0, 0, 0, 0.36)",
            "--color-shelf-dark": "#69496e",
            "--color-shelf-light": "#af7f71",
            "--theme-glow-left": "rgba(239, 186, 114, 0.26)",
            "--theme-glow-right": "rgba(146, 104, 162, 0.34)",
        },
    },
    {
        "id": "grand-oak-observatory",
        "name": "Grand Oak Observatory",
        "description": "A premium observatory library with polished oak, brass fixtures, and a cinematic midnight dome.",
        "source_kind": "showcase",
        "source_label": "Showcase pack",
        "source_reference": None,
        "is_builtin": True,
        "sort_order": 220,
        "family": "showcase",
        "preview_variant": "showpiece",
        "background_asset_path": "/theme-assets/backgrounds/grand-oak-observatory.svg",
        "background_overlay_path": "/theme-assets/textures/brass-stars.svg",
        "shelf_asset_path": "/theme-assets/shelves/grand-oak-shelf.svg",
        "surface_texture_asset_path": "/theme-assets/textures/woodgrain-dark.svg",
        "supports_mix_and_match": True,
        "tokens": {
            "--color-bg": "#0f1118",
            "--color-bg-elevated": "#171a24",
            "--color-panel": "rgba(23, 25, 36, 0.94)",
            "--color-panel-strong": "#322d3c",
            "--color-panel-soft": "rgba(39, 38, 52, 0.9)",
            "--color-text": "#f7f1e8",
            "--color-text-muted": "#dbcab5",
            "--color-border": "rgba(208, 170, 116, 0.22)",
            "--color-accent": "#e0ad67",
            "--color-accent-strong": "#9c6c35",
            "--color-danger": "#ffb4ab",
            "--color-success": "#8fd2ad",
            "--color-shadow": "rgba(0, 0, 0, 0.38)",
            "--color-shelf-dark": "#38291f",
            "--color-shelf-light": "#7c5a40",
            "--theme-glow-left": "rgba(224, 173, 103, 0.22)",
            "--theme-glow-right": "rgba(78, 96, 150, 0.28)",
        },
    },
)


def ensure_builtin_themes_seeded() -> None:
    ThemeProfile = _theme_profile_model()
    with db.session_scope() as session:
        existing_profiles = {
            profile.id: profile
            for profile in session.scalars(select(ThemeProfile).where(ThemeProfile.is_builtin.is_(True)))
        }

        for seed in BUILTIN_THEME_SEEDS:
            if seed["id"] in existing_profiles:
                profile = existing_profiles[str(seed["id"])]
                profile.family = str(seed.get("family", seed["source_kind"]))
                profile.preview_variant = str(seed.get("preview_variant", "standard"))
                profile.background_asset_path = seed.get("background_asset_path")
                profile.background_overlay_path = seed.get("background_overlay_path")
                profile.shelf_asset_path = seed.get("shelf_asset_path")
                profile.surface_texture_asset_path = seed.get("surface_texture_asset_path")
                profile.supports_mix_and_match = bool(seed.get("supports_mix_and_match", True))
                continue

            session.add(
                ThemeProfile(
                    id=str(seed["id"]),
                    name=str(seed["name"]),
                    description=seed["description"],
                    source_kind=str(seed["source_kind"]),
                    source_label=str(seed["source_label"]),
                    source_reference=seed["source_reference"],
                    is_builtin=bool(seed["is_builtin"]),
                    sort_order=int(seed["sort_order"]),
                    family=str(seed.get("family", seed["source_kind"])),
                    preview_variant=str(seed.get("preview_variant", "standard")),
                    background_asset_path=seed.get("background_asset_path"),
                    background_overlay_path=seed.get("background_overlay_path"),
                    shelf_asset_path=seed.get("shelf_asset_path"),
                    surface_texture_asset_path=seed.get("surface_texture_asset_path"),
                    supports_mix_and_match=bool(seed.get("supports_mix_and_match", True)),
                    tokens_json=json.dumps(seed["tokens"], sort_keys=True),
                )
            )


def list_themes(*, owner_user_id: int | None = None) -> list[ThemeSnapshot]:
    ThemeProfile = _theme_profile_model()
    ensure_builtin_themes_seeded()
    with db.session_scope() as session:
        statement = select(ThemeProfile).order_by(ThemeProfile.sort_order.asc(), ThemeProfile.name.asc())
        if owner_user_id is not None:
            statement = statement.where(
                ThemeProfile.is_builtin.is_(True) | (ThemeProfile.owner_user_id == owner_user_id)
            )
        profiles = list(
            session.scalars(statement)
        )
    return [_build_snapshot(profile) for profile in profiles]


def get_theme(theme_id: str, *, owner_user_id: int | None = None) -> ThemeSnapshot:
    ThemeProfile = _theme_profile_model()
    ensure_builtin_themes_seeded()
    with db.session_scope() as session:
        profile = session.get(ThemeProfile, theme_id)
        if profile is None or (owner_user_id is not None and not profile.is_builtin and profile.owner_user_id != owner_user_id):
            raise LookupError(f"Theme '{theme_id}' was not found")
    return _build_snapshot(profile)


def create_theme(
    *,
    name: str,
    source_kind: str,
    source_label: str,
    tokens: dict[str, str],
    description: str | None = None,
    source_reference: str | None = None,
    theme_id: str | None = None,
    family: str = "imported",
    preview_variant: str = "standard",
    background_asset_path: str | None = None,
    background_overlay_path: str | None = None,
    shelf_asset_path: str | None = None,
    surface_texture_asset_path: str | None = None,
    supports_mix_and_match: bool = True,
    owner_user_id: int | None = None,
) -> ThemeSnapshot:
    ThemeProfile = _theme_profile_model()
    normalized_id = _normalize_theme_id(theme_id or name)
    _validate_tokens(tokens)

    with db.session_scope() as session:
        existing = session.get(ThemeProfile, normalized_id)
        if existing is not None and (existing.is_builtin or existing.owner_user_id == owner_user_id):
            raise ValueError(f"Theme '{normalized_id}' already exists")
        if existing is not None and existing.owner_user_id != owner_user_id:
            normalized_id = f"{normalized_id}-{owner_user_id}"

        profile = ThemeProfile(
            id=normalized_id,
            owner_user_id=owner_user_id,
            name=name.strip(),
            description=description.strip() if description else None,
            source_kind=source_kind.strip(),
            source_label=source_label.strip(),
            source_reference=source_reference.strip() if source_reference else None,
            is_builtin=False,
            sort_order=1000,
            family=family.strip() if family.strip() else "imported",
            preview_variant=preview_variant.strip() if preview_variant.strip() else "standard",
            background_asset_path=background_asset_path.strip() if background_asset_path else None,
            background_overlay_path=background_overlay_path.strip() if background_overlay_path else None,
            shelf_asset_path=shelf_asset_path.strip() if shelf_asset_path else None,
            surface_texture_asset_path=surface_texture_asset_path.strip() if surface_texture_asset_path else None,
            supports_mix_and_match=bool(supports_mix_and_match),
            tokens_json=json.dumps(tokens, sort_keys=True),
        )
        session.add(profile)

    return get_theme(normalized_id, owner_user_id=owner_user_id)


def delete_theme(theme_id: str, *, owner_user_id: int | None = None) -> None:
    ThemeProfile = _theme_profile_model()
    with db.session_scope() as session:
        profile = session.get(ThemeProfile, theme_id)
        if profile is None:
            raise LookupError(f"Theme '{theme_id}' was not found")
        if profile.is_builtin:
            raise ValueError("Built-in themes cannot be deleted")
        if owner_user_id is not None and profile.owner_user_id != owner_user_id:
            raise LookupError(f"Theme '{theme_id}' was not found")
        session.delete(profile)


def theme_exists(theme_id: str, *, owner_user_id: int | None = None) -> bool:
    ThemeProfile = _theme_profile_model()
    ensure_builtin_themes_seeded()
    with db.session_scope() as session:
        profile = session.get(ThemeProfile, theme_id)
        if profile is None:
            return False
        if owner_user_id is None:
            return True
        return profile.is_builtin or profile.owner_user_id == owner_user_id


def _build_snapshot(profile: "ThemeProfile") -> ThemeSnapshot:
    return ThemeSnapshot(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        source_kind=profile.source_kind,
        source_label=profile.source_label,
        source_reference=profile.source_reference,
        is_builtin=profile.is_builtin,
        sort_order=profile.sort_order,
        family=profile.family,
        preview_variant=profile.preview_variant,
        background_asset_path=profile.background_asset_path,
        background_overlay_path=profile.background_overlay_path,
        shelf_asset_path=profile.shelf_asset_path,
        surface_texture_asset_path=profile.surface_texture_asset_path,
        supports_mix_and_match=profile.supports_mix_and_match,
        tokens=_load_tokens(profile.tokens_json),
    )


def _load_tokens(tokens_json: str) -> dict[str, str]:
    try:
        payload = json.loads(tokens_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Stored theme tokens are not valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Stored theme tokens must be a JSON object")

    tokens: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str):
            tokens[key] = value
    return tokens


def _validate_tokens(tokens: dict[str, str]) -> None:
    if not tokens:
        raise ValueError("Theme tokens are required")

    for token_name, token_value in tokens.items():
        if not token_name.startswith("--"):
            raise ValueError("Theme token names must start with '--'")
        if not token_value.strip():
            raise ValueError(f"Theme token '{token_name}' cannot be empty")


def _normalize_theme_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Theme id could not be derived from the provided name")
    return slug
