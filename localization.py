"""Cataloghi IT/EN centralizzati; nessuna dipendenza da SDL o dal motore."""

import json
import locale
import os
from pathlib import Path
from string import Formatter

from manifest import MANIFEST, ROOT


def system_language():
    override = os.environ.get('UPIX_LANGUAGE')
    if override:
        return override
    for name in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        if os.environ.get(name):
            return os.environ[name]
    if os.name == 'nt':
        import ctypes
        try:
            return locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), 'en')
        except (AttributeError, OSError):
            pass
    return locale.getlocale()[0] or 'en'


def _fields(value):
    if isinstance(value, list):
        return tuple(_fields(item) for item in value)
    if not isinstance(value, str):
        raise ValueError('Translation entries must be strings or lists of strings')
    return frozenset(name for _, name, _, _ in Formatter().parse(value) if name is not None)


class Localizer:
    def __init__(self, directory, language=None, *, fallback='en'):
        directory = Path(directory)
        self.catalogs = {code: json.loads((directory / f'{code}.json').read_text(encoding='utf-8'))
                         for code in ('it', 'en')}
        reference = self.catalogs[fallback]
        for catalog in self.catalogs.values():
            if catalog.keys() != reference.keys():
                raise ValueError('Translation catalogs have different keys')
            for key in reference:
                if _fields(catalog[key]) != _fields(reference[key]):
                    raise ValueError(f'Translation placeholders differ: {key}')
        code = (language or system_language()).replace('-', '_').split('_')[0].lower()
        self.language = code if code in self.catalogs else fallback

    def __getitem__(self, key):
        value = self.catalogs[self.language][key]
        return tuple(value) if isinstance(value, list) else value

    def text(self, key, **values):
        return self[key].format(**values)

    def set_language(self, language):
        if language not in self.catalogs:
            raise ValueError('Unsupported language')
        self.language = language

    def toggle(self):
        self.set_language('en' if self.language == 'it' else 'it')


I18N = Localizer(ROOT / MANIFEST['i18n']['directory'],
                 None if MANIFEST['i18n']['language'] == 'auto' else MANIFEST['i18n']['language'],
                 fallback=MANIFEST['i18n']['fallback'])
tr = I18N.text
