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
from game_state import GameState


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((upix.WIDTH, upix.HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.now_ms = 0
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = upix.Game(self.screen, time_source=lambda: self.now_ms)

    def tearDown(self):
        self.game._resume_audio()
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
                               0.155, delta=1 / 128)
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
        g.enemy_y = 560  # Il corpo 96x70 resta interamente fuori dal bordo sicuro.
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

    def test_runtime_missile_hits_thin_wall_before_trail_behind_it(self):
        g = self.game
        for y in range(upix.ROWS):
            g.grid[100][y] = upix.FILLED
        g.current_trail = [(110, 50)]
        g.drawing = True
        g.missiles = [{'x': 196, 'y': 100, 'vx': 30, 'vy': 0}]
        self.assertTrue(g._update_missiles())
        self.assertEqual(g.missiles, [])
        self.assertEqual(g.lives, 3)
        self.assertIsNone(g.physics_error)

    def test_runtime_high_speed_missile_hits_trail_only_once(self):
        g = self.game
        g.current_trail = [(80, 50)]
        g.drawing = True
        g.missiles = [{'x': 100, 'y': 100, 'vx': 100, 'vy': 0} for _ in range(2)]
        self.assertFalse(g._update_missiles())
        self.assertEqual(g.lives, 2)
        self.assertEqual(g.missiles, [])

    def test_new_player_segment_over_missile_causes_one_death_immediately(self):
        g = self.game
        g.missiles = [{'x': g.player_x * upix.CELL_SIZE,
                       'y': g.player_y * upix.CELL_SIZE - 3, 'vx': 0, 'vy': 0}]
        self.step(pygame.K_UP)
        self.assertEqual(g.lives, 2)
        self.assertEqual(g.missiles, [])
        self.assertFalse(g.drawing)

    def test_pause_freezes_simulation_input_clock_and_audio_without_restarting_loop(self):
        g = self.game
        self.step(pygame.K_UP, 3)
        g.missiles = [{'x': 100, 'y': 100, 'vx': 5, 'vy': 1}]
        self.now_ms = 100
        before = (g.enemy_x, g.enemy_y, g.player_x, g.player_y,
                  [dict(m) for m in g.missiles], list(g.current_trail))
        with mock.patch('pygame.mixer.pause', wraps=pygame.mixer.pause) as effects, \
                mock.patch('pygame.mixer.music.pause', wraps=pygame.mixer.music.pause) as music:
            g.pause()
            g.pause()
            effects.assert_called_once()
            music.assert_called_once()
        self.now_ms += 120_000
        g.update()
        self.step(pygame.K_RIGHT)
        g.draw()
        self.assertEqual(g.state, GameState.PAUSED)
        self.assertEqual(g.game_clock.elapsed_ms, 100)
        self.assertEqual(before, (g.enemy_x, g.enemy_y, g.player_x, g.player_y,
                                  g.missiles, g.current_trail))
        with mock.patch.object(g, 'draw_channel', wraps=g.draw_channel) as channel, \
                mock.patch('pygame.mixer.music.unpause', wraps=pygame.mixer.music.unpause) as music:
            g.toggle_pause()
            music.assert_called_once()
            channel.play.assert_not_called()
        self.assertEqual(g.state, GameState.PLAYING)
        self.assertTrue(g.draw_channel.get_busy())
        self.now_ms += 1
        g.update()
        self.assertEqual(g.game_clock.elapsed_ms, 101)
        self.assertAlmostEqual(g.enemy_x, before[0] + 3.3)
        self.assertEqual(g.missiles[0]['x'], 105)

    def test_pause_preserves_remaining_shot_and_direction_timers(self):
        g = self.game
        self.now_ms = g.shoot_interval - 50
        g.enemy_change_dir_timer = self.now_ms
        g.pause()
        self.now_ms += 60_000
        g.toggle_pause()
        with mock.patch('random.uniform', side_effect=AssertionError('AI anticipata')):
            g.update()
            self.assertEqual(g.missiles, [])
            self.now_ms += 51
            g.update()
        self.assertEqual(len(g.missiles), 1)
        self.assertEqual(g.last_shot_time, g.shoot_interval + 1)

    def test_terminal_states_ignore_pause_and_freeze_level_timer(self):
        g = self.game
        for state in (GameState.LEVEL_CLEAR, GameState.GAME_OVER, GameState.PHYSICS_ERROR):
            g._set_state(state)
            before = g.game_clock.elapsed_ms
            self.now_ms += 5000
            g.toggle_pause()
            self.assertEqual(g.state, state)
            self.assertEqual(g.game_clock.elapsed_ms, before)

    def test_capture_keeps_boss_region_open_and_reaches_win(self):
        g = self.game
        # Una linea verticale isola il boss in una stretta striscia a sinistra.
        g.enemy_x, g.enemy_y = 60, 300
        g.player_x, g.player_y = 60, upix.ROWS - 2
        g.current_trail = [(60, y) for y in range(1, upix.ROWS - 1)]
        g.drawing = True
        g.fill_area()
        self.assertEqual(g.grid[30][150], upix.EMPTY)
        self.assertEqual(g.grid[70][150], upix.FILLED)
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
                primary = upix.ASSET_DIR / "assets" / f"{level:02d}.png"
                cover = upix.ASSET_DIR / "assets" / f"{level:02d}.svg"
                self.assertTrue(primary.is_file())
                self.assertTrue(cover.is_file())
                g.level = level
                with contextlib.redirect_stdout(io.StringIO()):
                    g.start_level()
                self.assertEqual(g.primary_image_source, primary)
                self.assertEqual(g.cover_source, cover)
                self.assertNotEqual(g.canvas.get_at((100, 100))[:3], (0, 0, 0))
                g.draw()

    def test_svg_visible_initially_and_capture_reveals_primary_pixels(self):
        g = self.game
        before = g.canvas.get_at((100, 100))
        self.assertNotEqual(before[:3], (0, 0, 0))
        self.short_capture()
        self.assertEqual(g.canvas.get_at((405, 594)), g.hidden_image.get_at((405, 594)))
        self.assertEqual(g.canvas.get_at((100, 100)), before)

    def test_distinct_cover_and_primary_remain_separate_through_win(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            primary = pygame.Surface((upix.WIDTH, upix.HEIGHT))
            primary.fill((20, 40, 180))
            pygame.image.save(primary, str(root / "assets" / "01.png"))
            (root / "assets" / "01.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">'
                '<rect width="800" height="600" fill="#b42814"/></svg>', encoding="utf-8")
            g = self.game
            with mock.patch.object(upix, "ASSET_DIR", root):
                with contextlib.redirect_stdout(io.StringIO()):
                    g.start_level()
            self.assertEqual(g.canvas.get_at((100, 100))[:3], (180, 40, 20))
            self.assertEqual(g.hidden_image.get_at((100, 100))[:3], (20, 40, 180))
            self.short_capture()
            self.assertEqual(g.canvas.get_at((405, 594))[:3], (20, 40, 180))
            self.assertEqual(g.canvas.get_at((100, 100))[:3], (180, 40, 20))
            g._set_state(GameState.LEVEL_CLEAR)
            g.draw()
            self.assertEqual(self.screen.get_at((100, 100))[:3], (20, 40, 180))

    def test_boss_wall_regression_is_connected_to_runtime(self):
        g = self.game
        for y in range(upix.ROWS):
            g.grid[100][y] = upix.FILLED
        g.enemy_x, g.enemy_y = 151, 300
        g.enemy_vx, g.enemy_vy = 6.6, 0.75
        self.assertTrue(g._move_boss())
        self.assertAlmostEqual(g.enemy_x, 146.4)
        self.assertAlmostEqual(g.enemy_y, 300.75)
        self.assertAlmostEqual(g.enemy_vx, -6.6)
        self.assertIsNone(g.physics_error)

    def test_new_player_segment_hitting_boss_loses_one_life_without_capture(self):
        g = self.game
        g.enemy_x, g.enemy_y = 400, 560
        before = [column[:] for column in g.grid]
        self.step(pygame.K_UP)
        self.assertEqual(g.lives, 2)
        self.assertEqual(g.grid, before)
        self.assertFalse(g.draw_channel.get_busy())

    def test_capture_contact_leaves_canvas_and_grid_unchanged(self):
        g = self.game
        g.enemy_x, g.enemy_y = 400, 300
        g.current_trail = [(200, y) for y in range(1, upix.ROWS - 1)]
        g.drawing = True
        before = [column[:] for column in g.grid]
        pixels = pygame.image.tobytes(g.canvas, "RGB")
        g.fill_area()
        self.assertEqual(g.lives, 2)
        self.assertEqual(g.grid, before)
        self.assertEqual(pygame.image.tobytes(g.canvas, "RGB"), pixels)

    def test_invalid_physics_suspends_and_restart_level_recovers(self):
        g = self.game
        g.enemy_x = 4
        lives = g.lives
        self.assertFalse(g._move_boss())
        self.assertIsNotNone(g.physics_error)
        self.assertEqual(g.enemy_x, 4)
        self.assertEqual(g.lives, lives)
        g.draw()
        with contextlib.redirect_stdout(io.StringIO()):
            g.start_level()
        self.assertIsNone(g.physics_error)
        self.assertFalse(g.collision_grid.is_blocked(g._boss_body()))

    def test_boss_sprite_preserves_alpha_and_aspect_ratio(self):
        image = self.game.boss_img
        self.assertIsNotNone(image)
        self.assertEqual(image.get_size(), (96, 70))
        body = self.game._boss_body()
        self.assertEqual((body.width, body.height), image.get_size())
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
                    self.assertEqual((g._boss_body().width, g._boss_body().height), (96, 70))
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
