"""Small UTF-8 catalog: Italian and English, no compiled dependencies."""
import json
from pathlib import Path

with (Path(__file__).parent/'i18n'/'en.json').open(encoding='utf-8') as stream:
    EN=json.load(stream)
IT={english:italian for italian,english in EN.items()}


def translate(source,locale):
    if source in ('Prese fotografiche','Photo viewpoint'):return 'Photo viewpoint'
    return IT.get(source,source) if locale.lower().startswith('it') else EN.get(source,source)


def tr(source):
    # 0.6 deliberately uses English throughout the plugin UI.
    return translate(source,'en')
