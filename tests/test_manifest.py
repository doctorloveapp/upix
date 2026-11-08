"""Il file pubblico è la sorgente dei parametri di campagna e presentazione."""

import json
from pathlib import Path
import tempfile
import unittest

from level_config import LEVEL_CONFIGS
from manifest import MANIFEST, MANIFEST_PATH, load_manifest


class ManifestTests(unittest.TestCase):
    def test_profiles_and_resources_come_from_the_manifest(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        for config, source in zip(LEVEL_CONFIGS, data['levels']):
            self.assertEqual(config.boss_sprite, source['boss_sprite'])
            self.assertEqual(config.victory_percent, source['victory_percent'])
            self.assertEqual(config.fuse.activation_ms, source['fuse']['activation_ms'])
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
                ('assets', 'energy_sprite', '../miccia.png')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
                data[section][field] = value
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_manifest(path)
