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
        cover = data['level_cover']
        for key in ('transparency', 'halftone_strength'):
            value = cover[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'{key}: richiesto numero finito fra zero e uno')
        _positive(cover['halftone_spacing_px'], 'halftone_spacing_px')
        if cover['halftone_spacing_px'] > min(data['engine']['logical_size']):
            raise ValueError('Passo del retino maggiore del campo')
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
        for key in ('root', 'player_sprite', 'frame', 'energy_sprite', 'shield_sprite',
                    'life_sprite', 'music_dir', 'boss_dir', 'death_sound', 'menu_music',
                    'first_level_music'):
            _relative(data['assets'][key])
        frames = data['assets']['death_frames']
        if not isinstance(frames, list) or not frames or len(set(frames)) != len(frames):
            raise ValueError('Sequenza di morte vuota o duplicata')
        for frame_path in frames:
            _relative(frame_path)
        death = data['death_sequence']
        _positive(death['frame_duration_ms'], 'frame_duration_ms')
        for key in ('sprite_scale', 'sound_volume'):
            value = death[key]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('Presentazione morte non valida')
        if death['sprite_scale'] <= 0 or not 0 <= death['sound_volume'] <= 1:
            raise ValueError('Scala o volume morte non validi')
        _relative(data['i18n']['directory'])
        if data['i18n']['language'] not in ('auto', 'it', 'en') or data['i18n']['fallback'] not in ('it', 'en'):
            raise ValueError('Lingua non supportata')
        controller = data['controller']
        if not (0 <= controller['release_deadzone'] < controller['deadzone'] < 1):
            raise ValueError('Deadzone controller non valida')
        if (len(controller['axes']) != 2 or len(set(controller['axes'])) != 2
                or any(type(v) is not int or v < 0 for v in controller['axes'])
                or any(type(v) is not int or v < 0 for v in controller['buttons'].values())):
            raise ValueError('Mappa controller non valida')
        shield = data['shields']
        if not 0 < shield['capture_percent'] <= 100:
            raise ValueError('Soglia scudo non valida')
        for key in ('notice_ms', 'contact_grace_ms', 'ring_width', 'ring_padding'):
            _positive(shield[key], key)
        if len(shield['notice_sprite_size']) != 2:
            raise ValueError('Dimensioni avviso scudo non valide')
        for value in shield['notice_sprite_size']:
            _positive(value, 'notice_sprite_size')
        if (len(shield['ring_color']) != 3 or any(type(v) is not int or not 0 <= v <= 255
                                                for v in shield['ring_color'])):
            raise ValueError('Colore scudo non valido')
        if not 0 < data['progression']['extra_life_percent'] <= 100:
            raise ValueError('Soglia vita extra non valida')
        loop = data['progression']['loop']
        for key, value in loop.items():
            _positive(value, key)
        if (loop['max_speed_percent'] < 100 or loop['min_interval_percent'] > 100
                or not 0 < loop['max_victory_percent'] <= 100):
            raise ValueError('Progressione cicli non valida')
        threat = data['perimeter_threat']
        if type(threat['enabled']) is not bool:
            raise ValueError('Attivazione scossa non valida')
        speed = threat['speed_multiplier']
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
        for key in ('menu_fade_in_ms', 'menu_fade_out_ms'):
            if type(audio[key]) is not int or audio[key] < 0:
                raise ValueError(f'{key}: richiesti millisecondi interi non negativi')
        volume = audio['menu_music_volume']
        if type(volume) not in (int, float) or not math.isfinite(volume) or not 0 <= volume <= 1:
            raise ValueError('Volume musica menu non valido')
        if not audio['music_extensions'] or any(value != '.mp3' for value in audio['music_extensions']):
            raise ValueError('Estensioni musica non supportate')
        debug = data['debug_menu']
        for key in ('max_lives', 'max_shields'):
            _positive(debug[key], key)
        if debug['max_lives'] < engine['initial_lives']:
            raise ValueError('Limite debug inferiore alle vite normali')
        if not debug['sequence'] or any(value not in ('up', 'down', 'left', 'right', 'shield')
                                        for value in debug['sequence']):
            raise ValueError('Sequenza debug non valida')
        if not (0 <= audio['drawing_attenuation'] <= audio['music_volume'] <= 1
                and 0 <= audio['welding_volume'] <= 1):
            raise ValueError('Volumi non validi')
        ranking = data['leaderboard']
        _relative(ranking['file'])
        for key in ('limit', 'name_max_chars', 'max_score', 'max_file_bytes', 'max_completed_levels'):
            _positive(ranking[key], key)
        if ranking['name_max_chars'] > 32 or ranking['limit'] > 100:
            raise ValueError('Limiti classifica non supportati')
        levels = data['levels']
        if not levels or [item['number'] for item in levels] != list(range(1, len(levels) + 1)):
            raise ValueError('Livelli non consecutivi')
        for item in levels:
            required = {'boss_speed', 'missile_speed', 'missile_interval_ms', 'direction_interval_ms',
                        'direction_jitter', 'pursuit_weight', 'victory_percent', 'boss_render_scale',
                        'shock', 'scoring', 'hint'}
            if required - item.keys():
                raise ValueError('Profilo livello incompleto')
            for key in ('boss_speed', 'missile_speed', 'direction_jitter', 'pursuit_weight',
                        'victory_percent', 'boss_render_scale', 'perimeter_speed_px_per_second'):
                value = item[key]
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError(f'{key}: numero non finito')
            if (min(item['boss_speed'], item['missile_speed'], item['boss_render_scale']) <= 0
                    or item['direction_jitter'] < 0 or not 0 <= item['pursuit_weight'] <= 1
                    or not 0 < item['victory_percent'] <= 100
                    or item['perimeter_speed_px_per_second'] <= 0
                    or type(item['perimeter_threat_count']) is not int
                    or item['perimeter_threat_count'] not in (1, 2)):
                raise ValueError('Bilanciamento del livello non valido')
            _positive(item['direction_interval_ms'], 'direction_interval_ms')
            if item['missile_interval_ms'] is not None:
                _positive(item['missile_interval_ms'], 'missile_interval_ms')
            for key in ('boss_sprite', 'primary', 'cover'):
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
        for rect in [frame['game_area'], frame['footer'], *frame['values'].values(), *frame['labels'].values()]:
            x, y, w, h = rect
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
                raise ValueError('Geometria cornice fuori dai limiti')
        for color in data['colors'].values():
            if len(color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
                raise ValueError('Colore manifest non valido')
        if set(data['ui']['menu_actions']) != {'start', 'scores', 'tutorial', 'language', 'quit'} or len(data['ui']['menu_actions']) != 5:
            raise ValueError('Menu principale non valido')
        data['fingerprint'] = sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return _freeze(data)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Manifest incompleto o non valido: {exc}') from exc


MANIFEST = load_manifest()
