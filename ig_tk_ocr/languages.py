"""Discoverable OCR language selections; importing this module loads no models."""

import argparse

# These sets match PaddleOCR 3.7's language groups. v6 supports the Latin group
# except Pali; Cyrillic and Greek use their dedicated PP-OCRv5 recognizers.
PADDLE_V6_LANGUAGES = frozenset(
    "en pl ch chinese_cht af az bs ca cs cy da de es et eu fi fr ga gl hr hu "
    "id is it ku la lb lt lv mi ms mt nl no oc pt qu rm ro rs_latin sk sl sq sv "
    "sw tl tr uz vi japan".split()
)
PADDLE_CYRILLIC_LANGUAGES = frozenset(
    "ru rs_cyrillic be bg uk mn abq ady kbd ava dar inh che lbe lez tab kk ky "
    "tg mk tt cv ba mhr mo udm kv os bua xal tyv sah kaa".split()
)
PADDLE_LANGUAGES = PADDLE_V6_LANGUAGES | PADDLE_CYRILLIC_LANGUAGES | {"el"}

# All 24 official EU languages plus eight further European language/script
# selections. This is a practical preset, not automatic language detection.
EUROPE_LANGUAGES = tuple(
    "en bg hr fr hu fi sv de pl es pt el it nl da no cs sk sl ro et lv lt ga mt "
    "is uk ru rs_latin rs_cyrillic sq tr".split()
)
LANGUAGE_PRESETS = {
    "europe": EUROPE_LANGUAGES,
    "europe-latin": tuple(code for code in EUROPE_LANGUAGES
                          if code not in PADDLE_CYRILLIC_LANGUAGES and code != "el"),
}
LANGUAGE_NAMES = {
    "en": "English", "bg": "Bulgarian", "hr": "Croatian", "fr": "French",
    "hu": "Hungarian", "fi": "Finnish", "sv": "Swedish", "de": "German",
    "pl": "Polish", "es": "Spanish", "pt": "Portuguese", "el": "Greek",
    "it": "Italian", "nl": "Dutch", "da": "Danish", "no": "Norwegian",
    "cs": "Czech", "sk": "Slovak", "sl": "Slovene", "ro": "Romanian",
    "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian", "ga": "Irish",
    "mt": "Maltese", "is": "Icelandic", "uk": "Ukrainian", "ru": "Russian",
    "rs_latin": "Serbian (Latin)", "rs_cyrillic": "Serbian (Cyrillic)",
    "sq": "Albanian", "tr": "Turkish",
}


def _key(value):
    return value.strip().casefold().replace("-", "_").replace(" ", "_")


LANGUAGE_ALIASES = {_key(name): code for code, name in LANGUAGE_NAMES.items()}
LANGUAGE_ALIASES.update({
    "bulgaria": "bg", "croatia": "hr", "france": "fr", "hungary": "hu",
    "finland": "fi", "sweden": "sv", "germany": "de", "poland": "pl",
    "spain": "es", "portugal": "pt", "greece": "el", "italy": "it",
    "netherlands": "nl", "denmark": "da", "norway": "no", "czechia": "cs",
    "czech_republic": "cs", "slovakia": "sk", "slovenia": "sl", "slovenian": "sl",
    "romania": "ro", "estonia": "et", "latvia": "lv", "lithuania": "lt",
    "ireland": "ga", "malta": "mt", "iceland": "is", "ukraine": "uk",
    "russia": "ru", "albania": "sq", "turkey": "tr", "türkiye": "tr",
    "cz": "cs", "dk": "da", "ee": "et", "gr": "el", "se": "sv", "si": "sl",
    "serbian_latin": "rs_latin", "serbian_cyrillic": "rs_cyrillic", "ja": "japan",
})


def expand_languages(selection):
    """Expand presets/aliases into an ordered, unique tuple of language codes."""
    if isinstance(selection, str):
        selection = [selection]
    expanded = []
    for item in selection:
        if not isinstance(item, str):
            raise ValueError("OCR languages must be codes, names or presets; use --list-languages")
        for token in item.split(","):
            key = _key(token)
            if not key:
                raise ValueError("Empty OCR language selection; use --list-languages")
            preset = LANGUAGE_PRESETS.get(key.replace("_", "-"))
            codes = preset if preset else (LANGUAGE_ALIASES.get(key, key),)
            for code in codes:
                if code not in expanded:
                    expanded.append(code)
    if not expanded:
        raise ValueError("Provide at least one OCR language; use --list-languages")
    return tuple(expanded)


def validate_language_engine(languages, engine):
    """Reject known incompatible selections before importing or downloading OCR."""
    requested = set(languages)
    if engine == "paddle":
        unknown = requested - PADDLE_LANGUAGES
        if unknown:
            raise ValueError("Unsupported Paddle language code(s): " + ", ".join(sorted(unknown)) +
                             ". Run ig-tk-accnames-ocr --list-languages for codes and presets.")
    elif engine == "easyocr":
        # EasyOCR 1.7.2 does not offer these language codes. Do not claim that
        # substituting another language amounts to a Finnish/Greek OCR model.
        unavailable = requested & {"fi", "el"}
        mixed = bool(requested & PADDLE_CYRILLIC_LANGUAGES and
                     requested - PADDLE_CYRILLIC_LANGUAGES - {"en"})
        if unavailable or mixed:
            reasons = []
            if unavailable:
                reasons.append("EasyOCR does not provide " + ", ".join(
                    f"{LANGUAGE_NAMES[code]} ({code})" for code in sorted(unavailable)))
            if mixed:
                reasons.append("one EasyOCR reader cannot combine Latin and Cyrillic language groups")
            raise ValueError("; ".join(reasons) +
                             ". Use --engine paddle with the same --lang selection, "
                             "for example --engine paddle --lang europe. "
                             "EasyOCR can use --lang en pl or --lang en bg separately.")
    else:
        raise ValueError(f"Unknown OCR engine: {engine}")


def resolve_languages(selection, engine):
    languages = expand_languages(selection)
    validate_language_engine(languages, engine)
    return languages


def language_catalog():
    """Human-readable catalog, using only the standard library."""
    lines = [
        "OCR languages for IG-TK-AccNames-OCR",
        "",
        "Defaults: en pl. Codes, language names and the aliases below are accepted.",
        "Presets (use --engine paddle):",
        "  --lang europe        32 language/script selections; Latin + Cyrillic + Greek (3 readers)",
        "  --lang europe-latin  27 Latin-language selections (1 reader)",
        "  Presets expand once for the run; they do not detect a clip's language.",
        "",
        f"{'Code':<14}{'Language':<23}{'Paddle recognizer':<25}EasyOCR 1.7.2",
    ]
    for code in EUROPE_LANGUAGES:
        model = ("PP-OCRv5 Cyrillic" if code in PADDLE_CYRILLIC_LANGUAGES else
                 "PP-OCRv5 Greek" if code == "el" else "PP-OCRv6 Latin")
        easy = "not available" if code in {"fi", "el"} else (
            "Cyrillic + English" if code in PADDLE_CYRILLIC_LANGUAGES else "Latin group")
        lines.append(f"{code:<14}{LANGUAGE_NAMES[code]:<23}{model:<25}{easy}")
    lines.extend([
        "",
        "Examples: --lang en de pl | --lang en bg | --lang english french polish",
        "Aliases: Bulgaria -> bg, Croatia -> hr, France -> fr, Hungary -> hu,",
        "         Finland -> fi, Sweden -> sv, Germany -> de, Poland -> pl,",
        "         Spain -> es, Portugal -> pt; cz -> cs, gr -> el, se -> sv.",
        "Use uk for Ukrainian and eu for Basque; these are language codes, not region presets.",
        "For Serbian choose rs_latin or rs_cyrillic explicitly.",
        "",
        "Additional Paddle codes supported by this package:",
        "  v6: " + " ".join(sorted(PADDLE_V6_LANGUAGES - set(EUROPE_LANGUAGES))),
        "  Cyrillic v5: " + " ".join(sorted(PADDLE_CYRILLIC_LANGUAGES - set(EUROPE_LANGUAGES))),
        "Japanese (japan or ja) requires --paddle-size small or medium.",
        "Mixed script readers cost additional inference per crop. Conflicts stay visible for review.",
    ])
    return "\n".join(lines)


class ListLanguagesAction(argparse.Action):
    """An eager CLI listing, so no input/output arguments or OCR imports are needed."""
    def __init__(self, option_strings, dest=argparse.SUPPRESS, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(language_catalog())
        parser.exit()
