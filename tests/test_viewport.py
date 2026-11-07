"""Proiezione uniforme del fotogramma e coordinate ai bordi del viewport."""

import os
import unittest
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from viewport import Viewport
from hud import Hud, HudData
from pathlib import Path
import tempfile


class ViewportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.font.quit()
        pygame.display.quit()

    def test_1024_by_768_projection_has_no_distortion_or_offset(self):
        viewport = Viewport(pygame.Surface((1024, 768)), (800, 600))
        self.assertEqual(viewport.surface.get_size(), (800, 600))
        self.assertEqual(viewport.bounds, pygame.Rect(0, 0, 1024, 768))
        self.assertEqual(viewport.scale, 1.28)
        self.assertEqual(viewport.logical_to_window(400, 300), (512, 384))
        self.assertEqual(viewport.logical_to_window(800, 600), (1024, 768))
        for point in ((0, 0), (151.25, 200.5), (799, 599)):
            projected = viewport.logical_to_window(*point)
            restored = viewport.window_to_logical(*projected)
            self.assertAlmostEqual(restored[0], point[0])
            self.assertAlmostEqual(restored[1], point[1])
        self.assertIsNone(viewport.window_to_logical(1024, 768))

    def test_complete_frame_is_scaled_and_logical_surface_is_unchanged(self):
        window = pygame.Surface((1024, 768))
        viewport = Viewport(window, (800, 600))
        viewport.surface.fill((25, 30, 40))
        # Rappresentano elementi indipendenti del frame: sfondo, HUD e sprite.
        features = [((100, 100, 2, 2), (255, 50, 255)),
                    ((352, 265, 96, 70), (255, 0, 0)),
                    ((600, 400, 6, 6), (255, 100, 100)),
                    ((10, 10, 100, 20), (255, 255, 255))]
        for rect, color in features:
            viewport.surface.fill(color, rect)
        before = pygame.image.tobytes(viewport.surface, "RGB")
        with mock.patch('pygame.display.flip') as flip:
            viewport.present()
        flip.assert_called_once()
        for rect, color in features:
            x, y = pygame.Rect(rect).center
            px, py = viewport.logical_to_window(x, y)
            self.assertEqual(window.get_at((round(px), round(py)))[:3], color)
        self.assertEqual(window.get_at((1000, 750))[:3], (25, 30, 40))
        self.assertEqual(pygame.image.tobytes(viewport.surface, "RGB"), before)

    def test_other_aspect_ratio_uses_centered_letterbox_and_rejects_band_input(self):
        window = pygame.Surface((1200, 768))
        viewport = Viewport(window, (800, 600))
        viewport.surface.fill((10, 200, 30))
        self.assertEqual(viewport.bounds, pygame.Rect(88, 0, 1024, 768))
        self.assertEqual(viewport.logical_to_window(400, 300), (600, 384))
        self.assertIsNone(viewport.window_to_logical(87, 384))
        self.assertIsNone(viewport.window_to_logical(1112, 384))
        with mock.patch('pygame.display.flip'):
            viewport.present()
        self.assertEqual(window.get_at((0, 384))[:3], (0, 0, 0))
        self.assertEqual(window.get_at((1199, 384))[:3], (0, 0, 0))
        self.assertEqual(window.get_at((600, 384))[:3], (10, 200, 30))

    def test_hud_is_outside_playfield_and_shows_score_without_hiding_game_pixels(self):
        window = pygame.display.set_mode((1024, 768))
        hud = Hud(1024)
        viewport = Viewport(window, (800, 600), area=hud.game_area)
        data = HudData(1, 3, 12.5, 80, 12340, 65, 'Tutorial')
        viewport.surface.fill((30, 180, 50))
        self.assertEqual(viewport.bounds, pygame.Rect(52, 66, 917, 688))
        self.assertAlmostEqual(viewport.scale, 688 / 600)
        self.assertIsNone(viewport.window_to_logical(512, 47))
        self.assertEqual(viewport.window_to_logical(52, 66), (0, 0))
        with mock.patch('pygame.display.flip'):
            viewport.present(lambda target: hud.draw(target, data))
        self.assertEqual(window.get_at((512, 400))[:3], (30, 180, 50))
        first = pygame.image.tobytes(window.subsurface((0, 0, 1024, 65)), 'RGB')
        logo = pygame.image.tobytes(window.subsurface((0, 0, 260, 60)), 'RGB')
        with mock.patch('pygame.display.flip'):
            viewport.present(lambda target: hud.draw(
                target, HudData(1, 2, 25, 80, 99999, 65, 'Tutorial')))
        second = pygame.image.tobytes(window.subsurface((0, 0, 1024, 65)), 'RGB')
        self.assertNotEqual(first, second)
        self.assertEqual(pygame.image.tobytes(window.subsurface((0, 0, 260, 60)), 'RGB'), logo)
        self.assertEqual(window.get_at((512, 400))[:3], (30, 180, 50))

    def test_frame_values_are_inside_panels_and_missing_frame_keeps_game_visible(self):
        window = pygame.display.set_mode((1024, 768))
        with tempfile.TemporaryDirectory() as folder:
            hud = Hud(1024, frame_path=Path(folder) / 'missing.png')
        viewport = Viewport(window, (800, 600), area=hud.game_area)
        for bounds in hud.value_bounds.values():
            self.assertLessEqual(bounds.bottom, hud.game_area.top)
            self.assertTrue(window.get_rect().contains(bounds))
        viewport.surface.fill((20, 80, 120))
        with mock.patch('pygame.display.flip'):
            viewport.present(lambda target: hud.draw(target, HudData(12, 0, 100, 80, 1_200_000, 1, '')))
        self.assertEqual(window.get_at(viewport.bounds.center)[:3], (20, 80, 120))
