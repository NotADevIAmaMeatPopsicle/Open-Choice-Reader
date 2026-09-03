from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.themes import DEFAULT_THEME_ID, ThemeSnapshot, create_theme, get_theme


CSS_VARIABLE_PATTERN = re.compile(r"(?P<name>--[a-z0-9-]+)\s*:\s*(?P<value>[^;}{]+);", re.IGNORECASE)
CSS_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
THEME_SELECTOR_PATTERN = re.compile(r"\.bg-([a-z0-9-]+)", re.IGNORECASE)


@dataclass(frozen=True)
class ThemeImportMapping:
    source_variable: str
    target_token: str
    value: str


@dataclass(frozen=True)
class ThemeImportFallback:
    target_token: str
    source_variable: str | None
    value: str
    reason: str


@dataclass(frozen=True)
class KavitaThemeImportReport:
    detected_variable_count: int
    mapped_variables: list[ThemeImportMapping]
    ignored_variables: list[str]
    fallback_tokens: list[ThemeImportFallback]


@dataclass(frozen=True)
class KavitaThemeImportResult:
    theme: ThemeSnapshot
    report: KavitaThemeImportReport


TARGET_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("--color-bg", ("--bs-body-bg",), "identity"),
    ("--color-bg-elevated", ("--accent-bg-color", "--table-body-bg-color", "--bs-body-bg"), "identity"),
    ("--color-panel", ("--accent-bg-color", "--input-bg-color", "--table-body-bg-color"), "identity"),
    ("--color-panel-strong", ("--navbar-bg-color", "--table-header-bg-color", "--accent-bg-color"), "identity"),
    ("--color-panel-soft", ("--input-bg-color", "--accent-bg-color", "--table-body-bg-color"), "identity"),
    ("--color-text", ("--body-text-color", "--navbar-text-color", "--input-text-color"), "identity"),
    ("--color-text-muted", ("--text-muted-color", "--offwhite-text-color", "--search-result-text-lite-color"), "identity"),
    ("--color-border", ("--input-border-color", "--hr-color", "--tooltip-outline-color"), "identity"),
    ("--color-accent", ("--primary-color", "--colorscape-primary-default-color"), "identity"),
    (
        "--color-accent-strong",
        ("--primary-color-dark-shade", "--primary-color-darker-shade", "--primary-color"),
        "identity",
    ),
    ("--color-danger", ("--error-color",), "identity"),
    ("--color-success", tuple(), "identity"),
    ("--color-shadow", tuple(), "identity"),
    (
        "--color-shelf-dark",
        ("--primary-color-darkest-shade", "--colorscape-darker-default-color", "--navbar-bg-color"),
        "identity",
    ),
    (
        "--color-shelf-light",
        ("--primary-color-darker-shade", "--primary-color-dark-shade", "--colorscape-lighter-default-color", "--primary-color"),
        "identity",
    ),
    ("--theme-glow-left", ("--primary-color", "--colorscape-primary-default-color"), "glow-left"),
    (
        "--theme-glow-right",
        ("--primary-color-dark-shade", "--primary-color-darker-shade", "--navbar-bg-color", "--primary-color"),
        "glow-right",
    ),
)


SUPPORTED_SOURCE_VARIABLES = {candidate for _, candidates, _ in TARGET_RULES for candidate in candidates}


def import_kavita_theme(
    *,
    css_text: str,
    name: str | None,
    source_reference: str | None,
    owner_user_id: int | None = None,
) -> KavitaThemeImportResult:
    declared_variables = _extract_declared_variables(css_text)
    supported_declared = {key: value for key, value in declared_variables.items() if key in SUPPORTED_SOURCE_VARIABLES}

    if not supported_declared:
        raise ValueError("No supported Kavita theme variables were found in the provided CSS")

    base_theme = get_theme(DEFAULT_THEME_ID, owner_user_id=owner_user_id)
    tokens = dict(base_theme.tokens)
    mapped_variables: list[ThemeImportMapping] = []
    fallback_tokens: list[ThemeImportFallback] = []
    consumed_variables: set[str] = set()

    for target_token, candidate_variables, transform in TARGET_RULES:
        selected_variable = next((candidate for candidate in candidate_variables if candidate in supported_declared), None)
        if selected_variable is None:
            fallback_tokens.append(
                ThemeImportFallback(
                    target_token=target_token,
                    source_variable=None,
                    value=tokens[target_token],
                    reason="retained_default_theme_value",
                )
            )
            continue

        transformed_value = _transform_value(
            raw_value=supported_declared[selected_variable],
            transform=transform,
            fallback_value=tokens[target_token],
        )
        tokens[target_token] = transformed_value
        consumed_variables.add(selected_variable)
        mapped_variables.append(
            ThemeImportMapping(
                source_variable=selected_variable,
                target_token=target_token,
                value=transformed_value,
            )
        )

    imported_name = _resolve_theme_name(css_text=css_text, explicit_name=name, source_reference=source_reference)
    theme = create_theme(
        owner_user_id=owner_user_id,
        name=imported_name,
        description="Imported from a Kavita-compatible theme file.",
        source_kind="imported_kavita",
        source_label="Kavita import",
        source_reference=source_reference,
        tokens=tokens,
    )

    ignored_variables = sorted(variable for variable in declared_variables if variable not in consumed_variables)
    report = KavitaThemeImportReport(
        detected_variable_count=len(declared_variables),
        mapped_variables=mapped_variables,
        ignored_variables=ignored_variables,
        fallback_tokens=fallback_tokens,
    )
    return KavitaThemeImportResult(theme=theme, report=report)


def _extract_declared_variables(css_text: str) -> dict[str, str]:
    cleaned_css = CSS_COMMENT_PATTERN.sub("", css_text)
    declared_variables: dict[str, str] = {}
    for match in CSS_VARIABLE_PATTERN.finditer(cleaned_css):
        declared_variables[match.group("name").strip().lower()] = match.group("value").strip()
    return declared_variables


def _resolve_theme_name(*, css_text: str, explicit_name: str | None, source_reference: str | None) -> str:
    if explicit_name and explicit_name.strip():
        return explicit_name.strip()

    if source_reference:
        stem = re.sub(r"\.css$", "", source_reference.strip(), flags=re.IGNORECASE)
        if stem:
            return _titleize_slug(stem)

    selector_match = THEME_SELECTOR_PATTERN.search(css_text)
    if selector_match:
        return _titleize_slug(selector_match.group(1))

    return "Imported Kavita Theme"


def _titleize_slug(value: str) -> str:
    parts = [part for part in re.split(r"[^a-z0-9]+", value.lower()) if part]
    if not parts:
        return "Imported Kavita Theme"
    return " ".join(part.capitalize() for part in parts)


def _transform_value(*, raw_value: str, transform: str, fallback_value: str) -> str:
    if transform == "identity":
        return raw_value
    if transform == "glow-left":
        return _with_alpha(raw_value, alpha=0.18, fallback=fallback_value)
    if transform == "glow-right":
        return _with_alpha(raw_value, alpha=0.32, fallback=fallback_value)
    return fallback_value


def _with_alpha(value: str, *, alpha: float, fallback: str) -> str:
    normalized = value.strip()
    if normalized.startswith("#"):
        hex_color = normalized[1:]
        if len(hex_color) == 3:
            hex_color = "".join(channel * 2 for channel in hex_color)
        if len(hex_color) == 6:
            red = int(hex_color[0:2], 16)
            green = int(hex_color[2:4], 16)
            blue = int(hex_color[4:6], 16)
            return f"rgba({red}, {green}, {blue}, {alpha:.2f})"

    rgb_match = re.match(
        r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})(?:\s*[,/]\s*[\d.]+)?\s*\)",
        normalized,
        re.IGNORECASE,
    )
    if rgb_match:
        red, green, blue = rgb_match.groups()
        return f"rgba({red}, {green}, {blue}, {alpha:.2f})"

    return fallback
