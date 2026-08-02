import json
from pathlib import Path

_data: dict = json.loads((Path(__file__).parent / "locales.json").read_text(encoding="utf-8"))

SUPPORTED_LANGUAGES: dict[str, str] = _data["supported_languages"]
DEFAULT_LANG: str = _data["default_lang"]


def t(lang: str, key: str, **kwargs: object) -> str:
    strings = _data.get(lang, _data[DEFAULT_LANG])
    text = strings.get(key)
    if not isinstance(text, str):
        # Chiave assente o non testuale (es. la lista weekdays): si ripiega
        # sulla lingua di default, e in ultima istanza sulla chiave stessa.
        text = _data[DEFAULT_LANG].get(key)
        if not isinstance(text, str):
            return key
    return text.format(**kwargs) if kwargs else text


def get_weekdays(lang: str) -> list[str]:
    strings = _data.get(lang, _data[DEFAULT_LANG])
    result = strings.get("weekdays")
    if not isinstance(result, list):
        result = _data[DEFAULT_LANG]["weekdays"]
    return result


def lang_display_name(lang: str) -> str:
    return SUPPORTED_LANGUAGES.get(lang, lang)
