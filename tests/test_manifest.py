"""Il file pubblico è la sorgente dei parametri di campagna e presentazione."""

import json
from pathlib import Path
import tempfile
import unittest

from level_config import LEVEL_CONFIGS
from manifest import MANIFEST, MANIFEST_PATH, load_manifest


class ManifestTests(unittest.TestCase):
    def test_cover_controls_and_first_level_music_are_validated(self):
        for section, key, value in (
                ('level_cover', 'transparency', -0.1),
                ('level_cover', 'transparency', 1.1),
                ('level_cover', 'transparency', True),
                ('level_cover', 'halftone_strength', float('nan')),
                ('level_cover', 'halftone_spacing_px', 0),
                ('level_cover', 'halftone_spacing_px', 10_000),
                ('assets', 'first_level_music', '../02gold.mp3')):
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as folder:
                data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
                data[section][key] = value
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_manifest(path)

    def test_profiles_and_resources_come_from_the_manifest(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        for config, source in zip(LEVEL_CONFIGS, data['levels']):
            self.assertEqual(config.boss_sprite, source['boss_sprite'])
            self.assertEqual(config.victory_percent, source['victory_percent'])
            self.assertEqual(config.shock.activation_ms, source['shock']['activation_ms'])
            self.assertEqual(config.scoring.bonus_time_limit_ms, source['scoring']['bonus_time_limit_ms'])
        self.assertEqual([item.boss_sprite for item in LEVEL_CONFIGS[:5]],
                         [f'boss{level}.png' for level in range(1, 6)])
        with self.assertRaises(TypeError):
            MANIFEST['engine']['initial_lives'] = 9

    def test_custom_values_are_loaded_and_change_the_fingerprint(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        data['engine']['initial_lives'] = 5
        data['levels'][0]['boss_speed'] = 2.1
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'campaign.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            loaded = load_manifest(path)
        self.assertEqual(loaded['engine']['initial_lives'], 5)
        self.assertEqual(loaded['levels'][0]['boss_speed'], 2.1)
        self.assertNotEqual(loaded['fingerprint'], MANIFEST['fingerprint'])

    def test_invalid_manifest_rejected_before_starting_sdl(self):
        for field, value in (('cell_size', 0), ('logical_size', [801, 600]),
                             ('initial_lives', True), ('missile_size_scale', -1)):
            data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
            data['engine'][field] = value
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_manifest(path)
        data['assets']['root'] = '../private'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_invalid_perimeter_and_rotation_configuration_is_rejected(self):
        for section, field, value in (
                ('perimeter_threat', 'enabled', 1),
                ('perimeter_threat', 'speed_multiplier', 0),
                ('perimeter_threat', 'speed_multiplier', float('inf')),
                ('perimeter_threat', 'body_size', [0, 10]),
                ('perimeter_threat', 'sprite_max_size', [10]),
                ('energy_visual', 'rotation_step_degrees', 7),
                ('energy_visual', 'rotate_with_velocity', 'yes'),
                ('energy_visual', 'source_angle_degrees', float('nan')),
                ('assets', 'energy_sprite', '../shock.png')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
                data[section][field] = value
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_manifest(path)

    def test_death_presentation_requires_valid_assets_scale_timing_and_volume(self):
        for section, key, value in (
                ('assets', 'death_frames', []),
                ('assets', 'death_frames', ['icon/a.png', 'icon/a.png']),
                ('assets', 'death_frames', ['../a.png']),
                ('assets', 'death_sound', '../explosion.mp3'),
                ('death_sequence', 'frame_duration_ms', 0),
                ('death_sequence', 'sprite_scale', float('nan')),
                ('death_sequence', 'sprite_scale', -1),
                ('death_sequence', 'sound_volume', True),
                ('death_sequence', 'sound_volume', 2)):
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as folder:
                data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
                data[section][key] = value
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_manifest(path)

    def test_menu_music_path_fades_and_volume_are_validated(self):
        for section, key, value in (
                ('assets', 'menu_music', '../UPix.mp3'),
                ('audio', 'menu_fade_in_ms', -1),
                ('audio', 'menu_fade_out_ms', True),
                ('audio', 'menu_music_volume', float('nan')),
                ('audio', 'menu_music_volume', 1.1)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
                data[section][key] = value
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_manifest(path)
