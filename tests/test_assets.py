"""SVG reali: gradienti/testo, cache, fallback e proporzioni del viewport."""

from pathlib import Path
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import resvg_py
from assets import _svg_png, load_level_cover, load_level_image


class BackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_real_svg_gradient_visible_without_central_labels(self):
        root = Path(__file__).resolve().parents[1] / "public"
        image, source = load_level_cover(root, 1, (800, 600))
        self.assertEqual(source.name, "01.svg")
        self.assertEqual(image.get_size(), (800, 600))
        self.assertNotEqual(image.get_at((20, 20))[:3], (0, 0, 0))
        self.assertFalse(any(min(image.get_at((x, y))[:3]) > 200
                             for y in range(285, 315) for x in range(350, 450)))
        for level in range(1, 13):
            svg = ET.parse(root / "assets" / f"{level:02d}.svg")
            self.assertEqual(svg.findall(".//{http://www.w3.org/2000/svg}text"), [])

    def test_svg_cache_is_reused_without_rasterizing_each_load(self):
        _svg_png.cache_clear()
        root = Path(__file__).resolve().parents[1] / "public"
        with mock.patch("resvg_py.svg_to_bytes", wraps=resvg_py.svg_to_bytes) as render:
            for _ in range(2):
                image, _ = load_level_cover(root, 1, (800, 600))
                self.assertIsNotNone(image)
            self.assertEqual(render.call_count, 1)

    def test_changed_svg_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            path = root / "assets" / "01.svg"
            template = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="{}"/></svg>'
            path.write_text(template.format("red"), encoding="utf-8")
            first, _ = load_level_cover(root, 1, (8, 8))
            stamp = path.stat().st_mtime_ns
            path.write_text(template.format("blue"), encoding="utf-8")
            os.utime(path, ns=(stamp + 1_000_000_000, stamp + 1_000_000_000))
            second, _ = load_level_cover(root, 1, (8, 8))
            self.assertEqual(first.get_at((4, 4))[:3], (255, 0, 0))
            self.assertEqual(second.get_at((4, 4))[:3], (0, 0, 255))

    def test_corrupt_cover_or_missing_renderer_never_exposes_primary_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            image = pygame.Surface((8, 8))
            image.fill((20, 40, 60))
            pygame.image.save(image, str(root / "assets" / "01.png"))
            (root / "assets" / "01.svg").write_text("invalid SVG", encoding="utf-8")
            self.assertEqual(load_level_cover(root, 1, (8, 8)), (None, None))
            with mock.patch("assets._svg_png", side_effect=ImportError("renderer assente")):
                self.assertEqual(load_level_cover(root, 1, (8, 8)), (None, None))
            result, source = load_level_image(root, 1, (8, 8))
            self.assertEqual(source.suffix, ".png")
            self.assertEqual(result.get_at((4, 4))[:3], (20, 40, 60))

    def test_primary_missing_never_substitutes_svg(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            (root / "assets" / "01.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
                '<rect width="8" height="8" fill="red"/></svg>', encoding="utf-8")
            self.assertEqual(load_level_image(root, 1, (8, 8)), (None, None))
            cover, source = load_level_cover(root, 1, (8, 8))
            self.assertEqual(source.suffix, ".svg")
            self.assertEqual(cover.get_at((4, 4))[:3], (255, 0, 0))

    def test_primary_uses_jpg_when_png_is_corrupt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            (root / "assets" / "01.png").write_bytes(b"invalid PNG")
            image = pygame.Surface((8, 8))
            image.fill((20, 40, 60))
            pygame.image.save(image, str(root / "assets" / "01.jpg"))
            result, source = load_level_image(root, 1, (8, 8))
            self.assertEqual(source.suffix, ".jpg")
            self.assertEqual(result.get_size(), (8, 8))

    def test_primary_fills_entire_viewport_like_original_game(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            image = pygame.Surface((80, 60))
            image.fill((255, 0, 0))
            pygame.image.save(image, str(root / "assets" / "01.png"))
            result, _ = load_level_image(root, 1, (100, 100))
            self.assertEqual(result.get_size(), (100, 100))
            self.assertEqual(result.get_at((50, 0))[:3], (255, 0, 0))
            self.assertEqual(result.get_at((50, 50))[:3], (255, 0, 0))
            self.assertEqual(result.get_at((50, 99))[:3], (255, 0, 0))

    def test_real_svg_covers_1024_square_without_stretching_or_bands(self):
        root = Path(__file__).resolve().parents[1] / "public"
        result, source = load_level_cover(root, 1, (1024, 1024))
        self.assertEqual(source.suffix, ".svg")
        self.assertEqual(result.get_size(), (1024, 1024))
        self.assertNotEqual(result.get_at((512, 0))[:3], (0, 0, 0))
        self.assertNotEqual(result.get_at((512, 1023))[:3], (0, 0, 0))
        self.assertNotEqual(result.get_at((512, 512))[:3], (0, 0, 0))

    def test_wide_and_tall_primary_are_center_cropped_with_undistorted_markers(self):
        for size in ((200, 100), (100, 200)):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'assets').mkdir()
                image = pygame.Surface(size)
                image.fill((255, 0, 0))
                center = image.get_rect().center
                middle = pygame.Rect(0, 0, 100, 100)
                middle.center = center
                image.fill((0, 0, 255), middle)
                marker = pygame.Rect(0, 0, 40, 40)
                marker.center = center
                image.fill((255, 255, 255), marker)
                pygame.image.save(image, str(root / 'assets' / '01.png'))
                result, _ = load_level_image(root, 1, (100, 100))
                self.assertEqual(result.get_at((0, 0))[:3], (0, 0, 255))
                white = pygame.mask.from_threshold(result, (255, 255, 255), (1, 1, 1, 255))
                self.assertEqual(white.get_bounding_rects(), [pygame.Rect(30, 30, 40, 40)])

    def test_svg_cover_crops_source_aspect_before_raster_viewport_can_add_bands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'assets').mkdir()
            (root / 'assets' / '01.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
                '<rect width="200" height="100" fill="red"/>'
                '<rect x="50" width="100" height="100" fill="blue"/>'
                '<rect x="80" y="30" width="40" height="40" fill="white"/></svg>',
                encoding='utf-8')
            result, _ = load_level_cover(root, 1, (100, 100))
            self.assertEqual(result.get_at((0, 0))[:3], (0, 0, 255))
            white = pygame.mask.from_threshold(result, (255, 255, 255), (1, 1, 1, 255))
            self.assertEqual(white.get_bounding_rects(), [pygame.Rect(30, 30, 40, 40)])
