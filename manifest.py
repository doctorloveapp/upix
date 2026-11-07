"""Manifest JSON condiviso: nessuna dipendenza da Pygame o dal motore."""

from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / 'game_manifest.json'


def _relative(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
            or '..' in PurePosixPath(value).parts):
        raise ValueError(f'Percorso manifest non relativo: {value!r}')
    return value


def _positive(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f'{name}: richiesto intero positivo')


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def load_manifest(path=MANIFEST_PATH):
    """Fallisce prima dell'avvio se configurazione o riferimenti sono invalidi."""
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data['schema_version'] != 1 or type(data['schema_version']) is not int:
            raise ValueError('Versione manifest non supportata')
        if not isinstance(data['campaign_id'], str) or not data['campaign_id']:
            raise ValueError('Identificativo campagna mancante')
        engine = data['engine']
        for key in ('logical_size', 'window_size', 'player_max_size'):
            if len(engine[key]) != 2:
                raise ValueError(f'{key}: dimensioni non valide')
            for value in engine[key]:
                _positive(value, key)
        for key in ('cell_size', 'initial_lives', 'border_cells', 'simulation_hz',
                    'max_steps_per_frame', 'render_fps', 'capture_budget_ms',
                    'capture_chunk_cells', 'capture_max_chunks', 'missile_collision_size',
                    'missile_render_radius'):
            _positive(engine[key], key)
        if any(value % engine['cell_size'] for value in engine['logical_size']):
            raise ValueError('Campo non divisibile per le celle')
        if engine['border_cells'] * 2 >= min(engine['logical_size']) / engine['cell_size']:
            raise ValueError('Bordo troppo spesso')
        if engine['empty_cell'] == engine['filled_cell']:
            raise ValueError('Stati delle celle indistinguibili')
        for key in ('root', 'player_sprite', 'frame', 'energy_sprite'):
            _relative(data['assets'][key])
        threat = data['perimeter_threat']
        if type(threat['enabled']) is not bool:
            raise ValueError('Attivazione scossa non valida')
        speed = threat['speed_px_per_second']
        if type(speed) not in (int, float) or not math.isfinite(speed) or speed <= 0:
            raise ValueError('Velocità scossa non valida')
        for key in ('body_size', 'sprite_max_size'):
            if len(threat[key]) != 2:
                raise ValueError('Dimensioni scossa non valide')
            for value in threat[key]:
                _positive(value, key)
        visual = data['energy_visual']
        if type(visual['rotate_with_velocity']) is not bool:
            raise ValueError('Rotazione sprite non valida')
        _positive(visual['rotation_step_degrees'], 'rotation_step_degrees')
        if 360 % visual['rotation_step_degrees']:
            raise ValueError('Il passo di rotazione deve dividere 360')
        angle = visual['source_angle_degrees']
        if type(angle) not in (int, float) or not math.isfinite(angle):
            raise ValueError('Orientamento originale non valido')
        if (len(visual['fallback_color']) != 3 or any(type(v) is not int or not 0 <= v <= 255
                                                   for v in visual['fallback_color'])):
            raise ValueError('Colore fallback energia non valido')
        for value in data['assets']['welding_sounds']:
            _relative(value)
        if not data['assets']['primary_suffixes'] or any(
                value not in ('.png', '.jpg', '.jpeg') for value in data['assets']['primary_suffixes']):
            raise ValueError('Formati primari non supportati')
        audio = data['audio']
        if not (0 <= audio['drawing_attenuation'] <= audio['music_volume'] <= 1
                and 0 <= audio['welding_volume'] <= 1):
            raise ValueError('Volumi non validi')
        ranking = data['leaderboard']
        _relative(ranking['file'])
        for key in ('limit', 'name_max_chars', 'max_score', 'max_file_bytes'):
            _positive(ranking[key], key)
        if ranking['name_max_chars'] > 32 or ranking['limit'] > 100:
            raise ValueError('Limiti classifica non supportati')
        levels = data['levels']
        if not levels or [item['number'] for item in levels] != list(range(1, len(levels) + 1)):
            raise ValueError('Livelli non consecutivi')
        for item in levels:
            required = {'boss_speed', 'missile_speed', 'missile_interval_ms', 'direction_interval_ms',
                        'direction_jitter', 'pursuit_weight', 'victory_percent', 'boss_render_scale',
                        'fuse', 'scoring', 'hint'}
            if required - item.keys():
                raise ValueError('Profilo livello incompleto')
            for key in ('boss_speed', 'missile_speed', 'direction_jitter', 'pursuit_weight',
                        'victory_percent', 'boss_render_scale'):
                value = item[key]
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError(f'{key}: numero non finito')
            if (min(item['boss_speed'], item['missile_speed'], item['boss_render_scale']) <= 0
                    or item['direction_jitter'] < 0 or not 0 <= item['pursuit_weight'] <= 1
                    or not 0 < item['victory_percent'] <= 100):
                raise ValueError('Bilanciamento del livello non valido')
            _positive(item['direction_interval_ms'], 'direction_interval_ms')
            if item['missile_interval_ms'] is not None:
                _positive(item['missile_interval_ms'], 'missile_interval_ms')
            for key in ('boss_sprite', 'music', 'primary', 'cover'):
                _relative(item[key])
            if len(item['boss_max_size']) != 2:
                raise ValueError('Dimensioni boss non valide')
            for value in item['boss_max_size']:
                _positive(value, 'boss_max_size')
            if item['boss_render_scale'] * max(item['boss_max_size']) >= min(engine['logical_size']):
                raise ValueError('Boss troppo grande per il campo')
        if (type(engine['missile_size_scale']) not in (int, float)
                or not math.isfinite(engine['missile_size_scale']) or engine['missile_size_scale'] <= 0):
            raise ValueError('Scala proiettili non valida')
        frame = data['frame']
        width, height = frame['design_size']
        for rect in [frame['game_area'], frame['footer'], *frame['values'].values()]:
            x, y, w, h = rect
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
                raise ValueError('Geometria cornice fuori dai limiti')
        for color in data['colors'].values():
            if len(color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
                raise ValueError('Colore manifest non valido')
        if len(data['ui']['strings']['menu_items']) != 3:
            raise ValueError('Menu principale non valido')
        data['fingerprint'] = sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return _freeze(data)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Manifest incompleto o non valido: {exc}') from exc


MANIFEST = load_manifest()
