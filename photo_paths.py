"""Resolve photo references without accessing or downloading their contents."""
from .i18n import tr
from pathlib import Path
from urllib.parse import urlparse, unquote


def resolve_photo(reference, project_file='', layer_source=''):
    reference = reference.strip()
    if not reference:
        raise ValueError(tr('Questa presa non ha un riferimento nel campo photo.'))
    parsed = urlparse(reference)
    if parsed.scheme.lower() in ('http', 'https'):
        return None, reference
    if parsed.scheme.lower() == 'file':
        if parsed.netloc and parsed.netloc.lower() != 'localhost':
            reference = '//' + parsed.netloc + unquote(parsed.path)
        else:
            reference = unquote(parsed.path)
            if len(reference) > 2 and reference[0] == '/' and reference[2] == ':':
                reference = reference[1:]
    elif parsed.scheme and not (len(parsed.scheme) == 1 and len(reference) > 1 and reference[1] == ':'):
        raise ValueError(tr('Usa un percorso locale, un URL file:// o un URL https://.'))
    path = Path(reference).expanduser()
    if not path.is_absolute():
        if project_file:
            base = Path(project_file).parent
        else:
            source = layer_source.split('|', 1)[0]
            if not source or not Path(source).is_absolute():
                raise ValueError(tr('Per un percorso relativo salva prima il progetto oppure usa un percorso assoluto.'))
            base = Path(source).parent
        path = base / path
    return path, None
