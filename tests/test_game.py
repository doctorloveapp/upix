"""Regressioni del gameplay e dell'audio, senza finestra o altoparlanti."""
import collections
import contextlib
import io
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
import Upqix89 as upix


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((upix.WIDTH, upix.HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = upix.Game(self.screen)

    def tearDown(self):
        self.game._stop_draw_audio()
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def step(self, key=None, count=1):
        keys = collections.defaultdict(bool)
        if key is not None:
            keys[key] = True
        for _ in range(count):
            self.game._update_player(keys)

    def short_capture(self):
        self.step(pygame.K_UP, 3)
        self.step(pygame.K_RIGHT, 4)
        self.step(pygame.K_DOWN, 3)

    def test_spawn_and_safe_movement_are_silent(self):
        g = self.game
        self.assertEqual(g.grid[g.player_x][g.player_y], upix.FILLED)
        self.assertFalse(g.draw_channel.get_busy())
        self.step(pygame.K_RIGHT, 10)
        self.assertFalse(g.drawing)
        self.assertFalse(g.draw_channel.get_busy())
        self.assertEqual(g.sound_draw.get_num_channels(), 0)

    def test_drawing_starts_one_loop_and_ducks_music(self):
        g = self.game
        self.step(pygame.K_UP)
        self.assertTrue(g.drawing)
        self.assertEqual(g.grid[g.player_x][g.player_y], upix.EMPTY)
        self.assertTrue(g.draw_channel.get_busy())
        self.assertEqual(g.sound_draw.get_num_channels(), 1)
        self.assertAlmostEqual(pygame.mixer.music.get_volume(),
                               upix.DRAW_MUSIC_VOLUME, delta=1 / 128)
        # Non riavviare il campione a ogni frame o quando si cambia direzione.
        with mock.patch.object(g, "draw_channel", wraps=g.draw_channel) as channel:
            self.step(None, 5)
            self.step(pygame.K_RIGHT, 4)
            channel.play.assert_not_called()
        self.assertEqual(g.sound_draw.get_num_channels(), 1)

    def test_capture_stops_audio_and_updates_respawn(self):
        g = self.game
        self.short_capture()
        self.assertFalse(g.drawing)
        self.assertFalse(g.draw_channel.get_busy())
        self.assertEqual(g.current_trail, [])
        self.assertEqual(g.grid[g.player_x][g.player_y], upix.FILLED)
        self.assertEqual((g.last_safe_x, g.last_safe_y),
                         (g.player_x, g.player_y))
        self.assertGreater(g.score, 0)
        self.assertGreater(g.percent, 0)
        self.assertAlmostEqual(pygame.mixer.music.get_volume(),
                               upix.MUSIC_VOLUME, delta=1 / 128)
        self.step(pygame.K_RIGHT, 3)
        self.assertFalse(g.draw_channel.get_busy())
        self.step(pygame.K_UP)
        self.assertTrue(g.draw_channel.get_busy())

    def test_death_stops_audio_and_clears_pending_trail(self):
        g = self.game
        self.step(pygame.K_UP, 5)
        g.missiles.append({"x": 0})
        g.handle_death()
        self.assertEqual(g.lives, 2)
        self.assertFalse(g.draw_channel.get_busy())
        self.assertFalse(g.drawing)
        self.assertEqual(g.current_trail, [])
        self.assertEqual(g.missiles, [])
        self.assertEqual(g.grid[g.player_x][g.player_y], upix.FILLED)

    def test_final_death_stops_audio(self):
        self.game.lives = 1
        self.step(pygame.K_UP)
        self.game.handle_death()
        self.assertTrue(self.game.game_over)
        self.assertFalse(self.game.drawing)
        self.assertFalse(self.game.draw_channel.get_busy())

    def test_self_intersection_loses_exactly_one_life(self):
        self.step(pygame.K_UP, 4)
        self.step(pygame.K_RIGHT, 3)
        self.step(pygame.K_DOWN, 2)
        self.step(pygame.K_LEFT, 3)
        self.assertEqual(self.game.lives, 2)
        self.assertFalse(self.game.drawing)
        self.assertFalse(self.game.draw_channel.get_busy())

    def test_boss_hitting_trail_causes_death(self):
        g = self.game
        self.step(pygame.K_UP, 10)
        g.enemy_x = g.player_x * upix.CELL_SIZE
        g.enemy_y = g.player_y * upix.CELL_SIZE
        g.enemy_vx = g.enemy_vy = 0
        g.update()
        self.assertEqual(g.lives, 2)
        self.assertFalse(g.draw_channel.get_busy())

    def test_missile_hitting_trail_causes_death(self):
        g = self.game
        self.step(pygame.K_UP, 10)
        g.missiles = [{"x": g.player_x * upix.CELL_SIZE,
                       "y": g.player_y * upix.CELL_SIZE,
                       "vx": 0, "vy": 0}]
        g.update()
        self.assertEqual(g.lives, 2)
        self.assertFalse(g.draw_channel.get_busy())

    def test_safe_territory_absorbs_missiles(self):
        g = self.game
        g.missiles = [{"x": g.player_x * upix.CELL_SIZE,
                       "y": g.player_y * upix.CELL_SIZE,
                       "vx": 0, "vy": 0}]
        with mock.patch("pygame.key.get_pressed",
                        return_value=collections.defaultdict(bool)):
            g.update()
        self.assertEqual(g.lives, 3)
        self.assertEqual(g.missiles, [])
        self.assertFalse(g.draw_channel.get_busy())

    def test_capture_keeps_boss_region_open_and_reaches_win(self):
        g = self.game
        # Una linea verticale isola il boss in una stretta striscia a sinistra.
        g.enemy_x, g.enemy_y = 20, 300
        g.player_x, g.player_y = 20, upix.ROWS - 2
        g.current_trail = [(20, y) for y in range(1, upix.ROWS - 1)]
        g.drawing = True
        g.fill_area()
        self.assertEqual(g.grid[10][150], upix.EMPTY)
        self.assertEqual(g.grid[30][150], upix.FILLED)
        self.assertTrue(g.win)
        self.assertGreaterEqual(g.percent, 80)
        self.assertFalse(g.draw_channel.get_busy())

    def test_level_change_and_campaign_loop_reset_audio_and_music(self):
        g = self.game
        self.step(pygame.K_UP)
        g.next_level()
        self.assertEqual(g.level, 2)
        self.assertEqual(g.current_music_idx, 1)
        self.assertFalse(g.draw_channel.get_busy())
        g.level = g.max_levels
        g.next_level()
        self.assertEqual(g.level, 1)
        self.assertEqual(g.current_music_idx, 0)

    def test_restart_does_not_leave_old_draw_loop_playing(self):
        self.step(pygame.K_UP)
        with contextlib.redirect_stdout(io.StringIO()):
            replacement = upix.Game(self.screen)
        self.assertFalse(replacement.draw_channel.get_busy())
        self.assertEqual(replacement.lives, 3)

    def test_all_level_images_decode_and_render(self):
        g = self.game
        for level in range(1, g.max_levels + 1):
            with self.subTest(level=level):
                path = upix.ASSET_DIR / "assets" / f"{level:02d}.png"
                self.assertTrue(path.is_file())
                pygame.image.load(path)
                g.level = level
                with contextlib.redirect_stdout(io.StringIO()):
                    g.start_level()
                g.draw()

    def test_boss_sprite_preserves_alpha_and_aspect_ratio(self):
        image = self.game.boss_img
        self.assertIsNotNone(image)
        self.assertEqual(image.get_size(), (40, 29))
        self.assertTrue(image.get_flags() & pygame.SRCALPHA)
        self.assertIsNone(image.get_colorkey())
        self.assertEqual(image.get_at((0, 0)).a, 0)
        self.assertGreater(pygame.mask.from_surface(image).count(), 0)

    def test_boss_render_is_centered_at_rounded_physics_position(self):
        g = self.game
        g.enemy_x, g.enemy_y = 400.25, 300.75
        background = (17, 23, 31)
        g.canvas.fill(background)
        g.draw()
        bounds = g.boss_img.get_rect(center=(400, 301))
        expected = pygame.Surface(g.boss_img.get_size()).convert()
        expected.fill(background)
        expected.blit(g.boss_img, (0, 0))
        actual = self.screen.subsurface(bounds)
        self.assertEqual(pygame.image.tobytes(actual, "RGB"),
                         pygame.image.tobytes(expected, "RGB"))
        # Il rendering non deve quantizzare la posizione della simulazione.
        self.assertEqual((g.enemy_x, g.enemy_y), (400.25, 300.75))

    def test_unavailable_boss_sprite_keeps_physics_and_uses_primitive(self):
        # Il vecchio boss non deve diventare un fallback implicito.
        with tempfile.TemporaryDirectory() as folder:
            icons = Path(folder) / "icon"
            icons.mkdir()
            pygame.image.save(pygame.Surface((8, 8)), str(icons / "boss.png"))
            for corrupt in (False, True):
                with self.subTest(corrupt=corrupt):
                    if corrupt:
                        (icons / "boss2.png").write_bytes(b"invalid PNG")
                    with mock.patch.object(upix, "ASSET_DIR", Path(folder)):
                        with contextlib.redirect_stdout(io.StringIO()):
                            g = upix.Game(self.screen)
                    self.assertIsNone(g.boss_img)
                    self.assertEqual(g.enemy_radius, self.game.enemy_radius)
                    g.draw()
                    self.assertEqual(self.screen.get_at((400, 300))[:3],
                                     upix.COLOR_ENEMY)
                    g._stop_draw_audio()

    def test_assets_load_from_another_working_directory(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                with contextlib.redirect_stdout(io.StringIO()):
                    g = upix.Game(self.screen)
                self.assertIsNotNone(g.sound_draw)
                self.assertIsNotNone(g.cursor_img)
                self.assertIsNotNone(g.boss_img)
                g._stop_draw_audio()
            finally:
                os.chdir(previous)

    def test_missing_assets_fall_back_to_playable_game(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(upix, "ASSET_DIR", Path(folder)):
                with contextlib.redirect_stdout(io.StringIO()):
                    g = upix.Game(self.screen)
                self.assertIsNone(g.sound_draw)
                self.assertIsNone(g.cursor_img)
                self.assertIsNone(g.boss_img)
                g._update_player(collections.defaultdict(bool, {pygame.K_UP: True}))
                self.assertTrue(g.drawing)
                g.draw()

    def test_mp3_is_loaded_if_wav_is_unavailable(self):
        original = pygame.mixer.Sound

        def load(filename):
            if str(filename).endswith(".wav"):
                raise pygame.error("WAV non disponibile")
            return original(filename)

        with mock.patch("pygame.mixer.Sound", side_effect=load):
            with contextlib.redirect_stdout(io.StringIO()):
                g = upix.Game(self.screen)
        self.assertIsNotNone(g.sound_draw)
        g._update_player(collections.defaultdict(bool, {pygame.K_UP: True}))
        self.assertTrue(g.draw_channel.get_busy())
        g._stop_draw_audio()

    def test_unavailable_audio_device_does_not_crash(self):
        pygame.mixer.quit()
        try:
            with mock.patch("pygame.mixer.init", side_effect=pygame.error("No device")):
                with contextlib.redirect_stdout(io.StringIO()):
                    g = upix.Game(self.screen)
                g._update_player(collections.defaultdict(bool, {pygame.K_UP: True}))
                g.draw()
                self.assertIsNone(g.draw_channel)
        finally:
            pygame.mixer.init()

    def test_effect_has_prompt_non_silent_attack(self):
        # Verifica il campione realmente distribuito, non soltanto un mock.
        sound = pygame.mixer.Sound(str(upix.ASSET_DIR / "sounds" / "saldatrice.wav"))
        raw = sound.get_raw()[:4410 * 2 * 2]  # Primi 100 ms, stereo s16.
        samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
        rms = math.sqrt(sum(x * x for x in samples) / len(samples))
        self.assertGreater(rms, 500)


class ImportTests(unittest.TestCase):
    def test_import_does_not_initialize_pygame_or_open_a_window(self):
        result = subprocess.run(
            [sys.executable, "-c", "import Upqix89; import pygame; "
             "assert not pygame.get_init(); "
             "assert pygame.display.get_surface() is None"],
            cwd=upix.ASSET_DIR.parent, capture_output=True, text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
