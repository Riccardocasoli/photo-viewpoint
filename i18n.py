"""Small UTF-8 catalog: Italian with English fallback, no compiled dependencies."""
import json
from pathlib import Path

CATALOG = Path(__file__).parent / 'i18n'
EN = json.loads((CATALOG / 'en.json').read_text(encoding='utf-8'))
IT = {english: italian for italian, english in EN.items()}
IT.update(json.loads((CATALOG / 'it.json').read_text(encoding='utf-8')))


def translate(source, locale):
    if source in ('Prese fotografiche', 'Photo viewpoint'):
        return 'Photo viewpoint'
    english = EN.get(source, source)
    return IT.get(english, source) if locale.lower().startswith('it') else english


def tr(source):
    try:
        from qgis.core import QgsApplication
    except ImportError:
        return translate(source, 'en')
    return translate(source, QgsApplication.locale())
