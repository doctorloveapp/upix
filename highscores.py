"""Classifica personale versionata; adattatori filesystem e browser separati."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import sys
import unicodedata
from uuid import UUID

from manifest import MANIFEST, ROOT


class ScoreStoreError(ValueError):
    pass


def normalize_name(name):
    if not isinstance(name, str):
        raise ValueError('Nome non valido')
    name = ' '.join(unicodedata.normalize('NFKC', name).split())
    if (not name or len(name) > MANIFEST['leaderboard']['name_max_chars']
            or any(not (char.isalnum() or char in ' _-') for char in name)):
        raise ValueError('Nome non valido')
    return name


@dataclass(frozen=True, slots=True)
class ScoreEntry:
    run_id: str
    name: str
    score: int
    levels_completed: int
    elapsed_ms: int
    completed: bool
    created_at: str

    def __post_init__(self):
        try:
            UUID(self.run_id)
            stamp = datetime.fromisoformat(self.created_at)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError('Identificativi classifica non validi') from exc
        if stamp.tzinfo is None or normalize_name(self.name) != self.name:
            raise ValueError('Nome o data non normalizzati')
        if (type(self.score) is not int or not 0 <= self.score <= MANIFEST['leaderboard']['max_score']
                or type(self.levels_completed) is not int
                or not 0 <= self.levels_completed <= MANIFEST['leaderboard']['max_completed_levels']
                or type(self.elapsed_ms) is not int or self.elapsed_ms < 0
                or type(self.completed) is not bool):
            raise ValueError('Risultato classifica fuori intervallo')

    @classmethod
    def create(cls, run_id, name, score, levels_completed, elapsed_ms, completed):
        return cls(run_id, normalize_name(name), score, levels_completed, elapsed_ms,
                   completed, datetime.now(timezone.utc).isoformat())


class ScoreStore:
    """Codec condiviso; il motore non deve conoscere filesystem o localStorage."""

    def _read(self):
        raise NotImplementedError

    def _write(self, text):
        raise NotImplementedError

    def load(self):
        try:
            text = self._read()
            if text is None:
                return []
            if len(text.encode('utf-8')) > MANIFEST['leaderboard']['max_file_bytes']:
                raise ScoreStoreError('Classifica troppo grande')
            data = json.loads(text)
            if (type(data['schema_version']) is not int or data['schema_version'] != 1
                    or data['campaign_id'] != MANIFEST['campaign_id']
                    or not isinstance(data['entries'], list)):
                raise ScoreStoreError('Formato classifica incompatibile')
            entries = [ScoreEntry(**item) for item in data['entries']]
            if len({entry.run_id for entry in entries}) != len(entries):
                raise ScoreStoreError('Run duplicati nella classifica')
            return self._rank(entries)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ScoreStoreError(f'Classifica non leggibile: {exc}') from exc

    @staticmethod
    def _rank(entries):
        return sorted(entries, key=lambda entry: (-entry.score, -entry.levels_completed,
                      entry.elapsed_ms, entry.created_at, entry.run_id))[:MANIFEST['leaderboard']['limit']]

    def submit(self, entry: ScoreEntry):
        entries = self.load()  # Non sovrascrivere dati corrotti o versioni sconosciute.
        if any(item.run_id == entry.run_id for item in entries):
            return entries
        entries = self._rank([*entries, entry])
        text = json.dumps({'schema_version': 1, 'campaign_id': MANIFEST['campaign_id'],
                           'entries': [asdict(item) for item in entries]},
                          ensure_ascii=False, indent=2) + '\n'
        try:
            self._write(text)
        except OSError as exc:
            raise ScoreStoreError(f'Classifica non salvata: {exc}') from exc
        return entries


class JsonScoreStore(ScoreStore):
    def __init__(self, path=None):
        if path is not None:
            self.path = Path(path)
        elif getattr(sys, 'frozen', False):
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            self.path = base / 'UPIX1989' / Path(MANIFEST['leaderboard']['file']).name
        else:
            self.path = ROOT / MANIFEST['leaderboard']['file']

    def _read(self):
        try:
            with self.path.open(encoding='utf-8') as stream:
                return stream.read(MANIFEST['leaderboard']['max_file_bytes'] + 1)
        except FileNotFoundError:
            return None

    def _write(self, text):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.path.parent, prefix='.highscores-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class BrowserScoreStore(ScoreStore):
    """Storage Web iniettato: persistenza personale, NON classifica pubblica."""

    def __init__(self, storage):
        self.storage = storage
        self.key = MANIFEST['leaderboard']['storage_key']

    def _read(self):
        try:
            return self.storage.getItem(self.key)
        except Exception as exc:  # DOMException del bridge, non una OSError Python.
            raise ScoreStoreError('Storage browser non disponibile') from exc

    def _write(self, text):
        try:
            self.storage.setItem(self.key, text)
        except Exception as exc:
            raise ScoreStoreError('Storage browser pieno o disabilitato') from exc
