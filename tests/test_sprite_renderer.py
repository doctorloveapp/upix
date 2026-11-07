"""Orientamento con coordinate schermo, centratura e cache dei proiettili."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from manifest import MANIFEST, ROOT
from sprite_renderer import DirectionalSprite


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((80, 80))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_asymmetric_fixture_rotates_and_remains_centered(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'direction.png'
            source = pygame.Surface((8, 4), pygame.SRCALPHA)
            source.fill((255, 0, 0), (4, 0, 4, 4))
            pygame.image.save(source, str(path))
            renderer = DirectionalSprite(path, (8, 4), MANIFEST['energy_visual'])
        for velocity, expected in (((1, 0), 0), ((0, 1), 270), ((-1, 0), 180), ((0, -1), 90)):
            with self.subTest(velocity=velocity):
                self.assertEqual(renderer.angle_for(velocity), expected)
                target = pygame.Surface((40, 40), pygame.SRCALPHA)
                renderer.draw(target, (20, 20), velocity)
                reference = pygame.Surface((40, 40), pygame.SRCALPHA)
                frame = pygame.transform.rotate(renderer.image, expected)
                reference.blit(frame, frame.get_rect(center=(20, 20)))
                self.assertEqual(pygame.image.tobytes(target, 'RGBA'),
                                 pygame.image.tobytes(reference, 'RGBA'))
        right = renderer.frame_for((1, 0))
        down = renderer.frame_for((0, 1))
        self.assertEqual(right.get_at((6, 2)).a, 255)
        self.assertEqual(down.get_at((2, 6)).a, 255)  # punta rivolta in basso

    def test_cache_is_bounded_and_does_not_rotate_again_for_same_direction(self):
        renderer = DirectionalSprite(ROOT / 'public' / MANIFEST['assets']['energy_sprite'],
                                     (8, 8), MANIFEST['energy_visual'])
        self.assertIsNotNone(renderer.image)
        with mock.patch('pygame.transform.rotate', wraps=pygame.transform.rotate) as rotate:
            first = renderer.frame_for((1, 1))
            self.assertIs(renderer.frame_for((2, 2)), first)
            self.assertEqual(rotate.call_count, 1)
        import math
        for angle in range(720):
            renderer.frame_for((math.cos(math.radians(angle)), math.sin(math.radians(angle))))
        self.assertLessEqual(len(renderer._frames), 360 // renderer.step)

    def test_rotation_can_be_disabled_or_offset_and_missing_asset_has_fallback(self):
        config = dict(MANIFEST['energy_visual'], rotate_with_velocity=False)
        renderer = DirectionalSprite(ROOT / 'public/icon/miccia.png', (18, 18), config)
        self.assertEqual(renderer.angle_for((0, 1)), 0)
        renderer.rotate = True
        renderer.source_angle = 90
        self.assertEqual(renderer.angle_for((0, 1)), 0)
        with mock.patch('sprite_renderer.load_sprite', return_value=(None, (18, 18))):
            fallback = DirectionalSprite(Path('missing'), (18, 18), config)
        target = pygame.Surface((40, 40))
        fallback.draw(target, (20, 20), (1, 0))
        self.assertEqual(tuple(target.get_at((20, 20)))[:3], tuple(config['fallback_color']))


if __name__ == '__main__':
    unittest.main()
