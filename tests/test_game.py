"""Regressioni del gameplay e dell'audio, senza finestra o altoparlanti."""
import collections
import contextlib
import io
import math
import os
from pathlib import Path
import random
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
from shock_system import ShockSystem, ShockConfig
from perimeter_threat import PerimeterThreat
from territory import plan_capture


class GameTests(unittest.TestCase):
    def test_first_level_theme_switches_to_shuffle_and_returns_in_next_cycle(self):
        game = self.game
        self.assertEqual(game.music.current.name, '02gold.mp3')
        with mock.patch('pygame.mixer.music.load', wraps=pygame.mixer.music.load) as load:
            game._play_music()
            load.assert_not_called()
        with contextlib.redirect_stdout(io.StringIO()):
            game.next_level()
        self.assertEqual(game.level, 2)
        self.assertNotEqual(game.music.current.name, '02gold.mp3')
        game.level = 12
        game._set_state(GameState.CAMPAIGN_COMPLETE)
        with contextlib.redirect_stdout(io.StringIO()):
            game.continue_cycle()
        self.assertEqual((game.level, game.cycle), (1, 2))
        self.assertEqual(game.music.current.name, '02gold.mp3')

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
        self.game.cancel_death()
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
        self.finish_capture()

    def finish_death(self):
        for _ in range(100):
            if self.game.state != GameState.DYING:
                return
            self.now_ms += 17
            self.game.advance_frame(collections.defaultdict(bool))
        self.fail('La sequenza di morte non termina')

    def finish_capture(self):
        for _ in range(10_000):
            if self.game.state != GameState.CAPTURING:
                return
            self.game.advance_frame(collections.defaultdict(bool))
        self.fail("La cattura non termina")

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
        self.step(pygame.K_RIGHT, 3)  # Segue il nuovo confine, senza attraversare l'interno.
        self.assertFalse(g.draw_channel.get_busy())
        self.step(pygame.K_UP)
        self.assertTrue(g.draw_channel.get_busy())

    def test_death_stops_audio_and_clears_pending_trail(self):
        g = self.game
        self.step(pygame.K_UP, 5)
        g.missiles.append({"x": 0})
        g.handle_death()
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertFalse(g.draw_channel.get_busy())
        self.assertEqual(g.state, GameState.DYING)
        self.assertTrue(g.drawing)
        self.finish_death()
        self.assertFalse(g.drawing)
        self.assertEqual(g.current_trail, [])
        self.assertEqual(g.missiles, [])
        self.assertEqual(g.grid[g.player_x][g.player_y], upix.FILLED)

    def test_final_death_stops_audio(self):
        self.game.lives = 1
        self.step(pygame.K_UP)
        self.game.handle_death()
        self.assertEqual(self.game.state, GameState.DYING)
        self.finish_death()
        self.assertTrue(self.game.game_over)
        self.assertFalse(self.game.drawing)
        self.assertFalse(self.game.draw_channel.get_busy())

    def test_self_intersection_loses_exactly_one_life(self):
        self.step(pygame.K_UP, 4)
        self.step(pygame.K_RIGHT, 3)
        self.step(pygame.K_DOWN, 2)
        self.step(pygame.K_LEFT, 3)
        self.assertEqual(self.game.lives, upix.ENGINE['initial_lives'] - 1)
        self.finish_death()
        self.assertFalse(self.game.drawing)
        self.assertFalse(self.game.draw_channel.get_busy())

    def test_boss_hitting_trail_causes_death(self):
        g = self.game
        self.step(pygame.K_UP, 10)
        g.enemy_x = g.player_x * upix.CELL_SIZE
        g.enemy_y = 540  # Il nuovo corpo 134x98 resta libero e interseca la scia.
        g.enemy_vx = g.enemy_vy = 0
        g.update()
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertFalse(g.draw_channel.get_busy())

    def test_missile_hitting_trail_causes_death(self):
        g = self.game
        self.step(pygame.K_UP, 10)
        g.missiles = [{"x": g.player_x * upix.CELL_SIZE,
                       "y": g.player_y * upix.CELL_SIZE,
                       "vx": 0, "vy": 0}]
        g.update()
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertFalse(g.draw_channel.get_busy())

    def test_safe_territory_absorbs_missiles(self):
        g = self.game
        g.missiles = [{"x": g.player_x * upix.CELL_SIZE,
                       "y": g.player_y * upix.CELL_SIZE,
                       "vx": 0, "vy": 0}]
        with mock.patch("pygame.key.get_pressed",
                        return_value=collections.defaultdict(bool)):
            g.update()
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'])
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
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'])
        self.assertIsNone(g.physics_error)

    def test_runtime_high_speed_missile_hits_trail_only_once(self):
        g = self.game
        g.current_trail = [(80, 50)]
        g.drawing = True
        g.missiles = [{'x': 100, 'y': 100, 'vx': 100, 'vy': 0} for _ in range(2)]
        self.assertFalse(g._update_missiles())
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertEqual(g.state, GameState.DYING)
        self.assertEqual(len(g.missiles), 1)  # Il secondo missile resta congelato.
        self.finish_death()
        self.assertEqual(g.missiles, [])

    def test_new_player_segment_over_missile_causes_one_death_immediately(self):
        g = self.game
        g.missiles = [{'x': g.player_x * upix.CELL_SIZE,
                       'y': g.player_y * upix.CELL_SIZE - 3, 'vx': 0, 'vy': 0}]
        self.step(pygame.K_UP)
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertEqual(g.missiles, [])
        self.assertFalse(g.drawing)

    def test_pause_freezes_simulation_input_clock_and_audio_without_restarting_loop(self):
        g = self.game
        self.step(pygame.K_UP, 3)
        self.now_ms = 100
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 6)
        g.missiles = [{'x': 100, 'y': 100, 'vx': 5, 'vy': 1}]
        before = (g.enemy_x, g.enemy_y, g.player_x, g.player_y,
                  [dict(m) for m in g.missiles], list(g.current_trail))
        with mock.patch('pygame.mixer.pause', wraps=pygame.mixer.pause) as effects, \
                mock.patch('pygame.mixer.music.pause', wraps=pygame.mixer.music.pause) as music:
            g.pause()
            g.pause()
            effects.assert_called_once()
            music.assert_called_once()
        self.now_ms += 120_000
        self.assertEqual(g.advance_frame(), 0)
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
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 0)
        self.now_ms += 16
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 1)
        self.assertEqual(g.game_clock.elapsed_ms, 116)
        self.assertAlmostEqual(g.enemy_x, before[0] + g.level_config.boss_speed / math.sqrt(2))
        self.assertEqual(g.missiles[0]['x'], 105)

    def test_pause_preserves_remaining_shot_and_direction_timers(self):
        g = self.game
        g.level = 2
        with contextlib.redirect_stdout(io.StringIO()):
            g.start_level()
        keys = collections.defaultdict(bool)
        shot_ticks = (g.shoot_interval * 60 + 999) // 1000
        for _ in range(shot_ticks - 2):
            g.update(keys)
        g.enemy_change_dir_timer = g.game_clock.elapsed_ms
        g.pause()
        self.now_ms += 60_000
        g.toggle_pause()
        with mock.patch.object(g.rng, 'uniform', side_effect=AssertionError('AI anticipata')):
            self.now_ms += 17
            self.assertEqual(g.advance_frame(keys), 1)
            self.assertEqual(g.missiles, [])
            self.now_ms += 17
            self.assertEqual(g.advance_frame(keys), 1)
        self.assertEqual(len(g.missiles), 1)
        self.assertEqual(g.last_shot_time, g.shoot_interval)

    def test_seeded_game_simulation_matches_at_30_60_and_144_render_fps(self):
        snapshots = []
        keys = collections.defaultdict(bool, {pygame.K_LEFT: True})
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                self.now_ms = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    g = upix.Game(self.screen, time_source=lambda: self.now_ms,
                                  rng=random.Random(1989))
                    g.level = 2
                    g.start_level()
                try:
                    for frame in range(1, fps * 3 + 1):
                        self.now_ms = frame * 1000 // fps
                        g.advance_frame(keys)
                        g.draw()
                    self.assertEqual(g.game_clock.ticks, 180)
                    self.assertEqual(g.frame_clock.dropped_ticks, 0)
                    self.assertEqual(g.last_shot_time, 2250)
                    self.assertEqual(g.enemy_change_dir_timer, 3000)
                    self.assertEqual(g.player_x, upix.COLS // 2 - 180)
                    snapshots.append((g.enemy_x, g.enemy_y, g.enemy_vx, g.enemy_vy,
                                      g.missiles, g.player_x, g.player_y, g.state,
                                      g.lives, g.score, g.percent, g.game_clock.ticks,
                                      g.rng.getstate()))
                finally:
                    g._stop_draw_audio()
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])

    def test_fixed_ticks_keep_boss_and_missile_wall_regression_deterministic(self):
        snapshots = []
        for fps in (30, 60, 144):
            origin_ms = self.now_ms
            g = self.game
            with contextlib.redirect_stdout(io.StringIO()):
                g.start_level()
            for y in range(upix.ROWS):
                g.grid[100][y] = upix.FILLED  # Parete logica x=200..201 px.
            g.enemy_x, g.enemy_y = 200 - g.boss_size[0] / 2 - 1, 300
            g.enemy_vx, g.enemy_vy = 6.6, 0.75
            g.missiles = [{'x': 190, 'y': 100, 'vx': 40, 'vy': 0}]
            for frame in range(1, fps // 10 + 1):
                self.now_ms = origin_ms + min(100, frame * 1000 // fps)
                g.advance_frame(collections.defaultdict(bool))
            self.now_ms = origin_ms + 100
            g.advance_frame(collections.defaultdict(bool))
            self.assertEqual(g.game_clock.ticks, 6)
            self.assertEqual(g.missiles, [])
            self.assertEqual(g.lives, upix.ENGINE['initial_lives'])
            self.assertEqual(g.state, GameState.PLAYING)
            self.assertLessEqual(g._boss_body().right, 200)
            snapshots.append((g.enemy_x, g.enemy_y, g.enemy_vx, g.enemy_vy))
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])

    def test_terminal_state_interrupts_catchup_and_new_level_clears_credit(self):
        g = self.game
        g.lives = 1
        g.drawing = True
        g.player_x, g.player_y = 100, 100
        g.current_trail = [(100, 100)]
        g.missiles = [{'x': 190, 'y': 201, 'vx': 40, 'vy': 0}]
        self.now_ms = 100
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 1)
        self.assertEqual(g.state, GameState.DYING)
        self.assertEqual(g.game_clock.ticks, 1)
        self.finish_death()
        self.assertEqual(g.state, GameState.GAME_OVER)
        self.now_ms += 120_000
        with contextlib.redirect_stdout(io.StringIO()):
            g.start_level()
        self.assertEqual(g.game_clock.ticks, 0)
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 0)
        self.now_ms += 17
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 1)

    def test_drawing_does_not_advance_simulation_or_present_display(self):
        g = self.game
        self.now_ms = 1000
        before = (g.enemy_x, g.enemy_y, g.game_clock.ticks, g.rng.getstate())
        with mock.patch('pygame.display.flip') as flip:
            g.draw()
            g.draw()
        flip.assert_not_called()
        self.assertEqual(before, (g.enemy_x, g.enemy_y, g.game_clock.ticks, g.rng.getstate()))

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
        g.enemy_x, g.enemy_y = 75, 300
        g.player_x, g.player_y = 80, upix.ROWS - 2
        g.current_trail = [(80, y) for y in range(1, upix.ROWS - 1)]
        g.drawing = True
        g.fill_area()
        self.finish_capture()
        self.assertEqual(g.grid[30][150], upix.EMPTY)
        self.assertEqual(g.grid[90][150], upix.FILLED)
        self.assertTrue(g.win)
        self.assertGreaterEqual(g.percent, 80)
        self.assertFalse(g.draw_channel.get_busy())

    def test_same_capture_clears_tutorial_but_not_final_level_target(self):
        g = self.game
        for level, should_win in ((1, True), (12, False)):
            g.level = level
            with contextlib.redirect_stdout(io.StringIO()):
                g.start_level()
            g.enemy_x, g.enemy_y = 100, 300
            g.player_x, g.player_y = 100, upix.ROWS - 2
            g.current_trail = [(100, y) for y in range(1, upix.ROWS - 1)]
            g.drawing = True
            g.fill_area()
            self.finish_capture()
            self.assertGreater(g.percent, 74)
            self.assertLess(g.percent, 80)
            self.assertEqual(g.win, should_win)

    def test_level_change_and_campaign_end_reset_audio_without_looping(self):
        g = self.game
        self.step(pygame.K_UP)
        g.next_level()
        self.assertEqual(g.level, 2)
        self.assertIn(g.music.current, g.music.shuffle.tracks)
        self.assertFalse(g.draw_channel.get_busy())
        g.level = g.max_levels
        g.next_level()
        self.assertEqual(g.level, g.max_levels)
        self.assertEqual(g.state, GameState.CAMPAIGN_COMPLETE)

    def test_restart_does_not_leave_old_draw_loop_playing(self):
        self.step(pygame.K_UP)
        with contextlib.redirect_stdout(io.StringIO()):
            replacement = upix.Game(self.screen)
        self.assertFalse(replacement.draw_channel.get_busy())
        self.assertEqual(replacement.lives, upix.ENGINE['initial_lives'])

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
                self.assertEqual((g._boss_body().width, g._boss_body().height),
                                 g.boss_img.get_size())
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
            preview = g.canvas.get_at((100, 100))[:3]
            self.assertNotEqual(preview, (180, 40, 20))
            self.assertNotEqual(preview, (20, 40, 180))
            self.assertEqual(g.hidden_image.get_at((100, 100))[:3], (20, 40, 180))
            self.short_capture()
            self.assertEqual(g.canvas.get_at((405, 594))[:3], (20, 40, 180))
            self.assertEqual(g.canvas.get_at((100, 100))[:3], preview)
            g._set_state(GameState.LEVEL_CLEAR)
            g.draw()
            self.assertEqual(self.screen.get_at((100, 100))[:3], (20, 40, 180))

    def test_boss_wall_regression_is_connected_to_runtime(self):
        g = self.game
        for y in range(upix.ROWS):
            g.grid[100][y] = upix.FILLED
        start = 200 - g.boss_size[0] / 2 - 1
        g.enemy_x, g.enemy_y = start, 300
        g.enemy_vx, g.enemy_vy = 6.6, 0.75
        self.assertTrue(g._move_boss())
        self.assertAlmostEqual(g.enemy_x, start - 4.6)
        self.assertAlmostEqual(g.enemy_y, 300.75)
        self.assertAlmostEqual(g.enemy_vx, -6.6)
        self.assertIsNone(g.physics_error)

    def test_new_player_segment_hitting_boss_loses_one_life_without_capture(self):
        g = self.game
        g.enemy_x, g.enemy_y = 400, 546
        before = [column[:] for column in g.grid]
        self.step(pygame.K_UP)
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
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
        self.finish_capture()
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertEqual(g.grid, before)
        self.assertEqual(pygame.image.tobytes(g.canvas, "RGB"), pixels)

    def test_capture_runs_in_blocks_and_commits_the_reference_plan_once(self):
        g = self.game
        g.enemy_x, g.enemy_y = 200, 300
        g.player_x, g.player_y = 200, upix.ROWS - 2
        g.current_trail = [(200, y) for y in range(1, upix.ROWS - 1)]
        g.drawing = True
        expected = plan_capture(g.collision_grid, g.current_trail, g._boss_body())
        before_grid = [column[:] for column in g.grid]
        before_canvas = pygame.image.tobytes(g.canvas, 'RGB')
        before = (g.enemy_x, g.enemy_y, g.game_clock.ticks, g.score, g.percent)
        g.fill_area()
        self.assertEqual(g.state, GameState.CAPTURING)
        with mock.patch.object(upix, 'CAPTURE_MAX_CHUNKS', 1):
            for _ in range(5):
                self.now_ms += 17
                self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 0)
                g.draw()
                self.assertEqual(g.grid, before_grid)
                self.assertEqual(pygame.image.tobytes(g.canvas, 'RGB'), before_canvas)
                self.assertEqual(before, (g.enemy_x, g.enemy_y, g.game_clock.ticks,
                                          g.score, g.percent))
        self.finish_capture()
        actual = {(x, y) for x in range(upix.COLS) for y in range(upix.ROWS)
                  if g.grid[x][y] != before_grid[x][y]}
        self.assertEqual(actual, set(expected.cells))
        base = expected.area_count * g.level_config.scoring.points_per_cell
        bonus = base * expected.area_count // (upix.COLS * upix.ROWS)
        self.assertEqual(g.score, base + bonus)
        self.assertEqual(g._filled_cells, sum(column.count(upix.FILLED) for column in g.grid))
        self.assertAlmostEqual(g.percent, g._filled_cells * 100 / (upix.COLS * upix.ROWS))
        self.assertFalse(g.collision_grid.is_blocked(g._boss_body()))
        score = g.score
        g.advance_frame(collections.defaultdict(bool))
        self.assertEqual(g.score, score)

    def test_pause_during_capture_preserves_job_and_resumes_without_time_debt(self):
        g = self.game
        self.step(pygame.K_UP, 3)
        self.step(pygame.K_RIGHT, 4)
        self.step(pygame.K_DOWN, 3)
        self.assertEqual(g.state, GameState.CAPTURING)
        job = g._capture_work
        ticks = g.game_clock.ticks
        g.pause()
        self.now_ms += 120_000
        self.assertEqual(g.advance_frame(), 0)
        self.assertIs(g._capture_work, job)
        self.assertEqual(g.state, GameState.PAUSED)
        g.toggle_pause()
        self.assertEqual(g.state, GameState.CAPTURING)
        self.finish_capture()
        self.assertEqual(g.state, GameState.PLAYING)
        self.assertEqual(g.game_clock.ticks, ticks)
        self.assertGreater(g.score, 0)
        self.assertEqual(g.advance_frame(collections.defaultdict(bool)), 0)

    def test_staging_is_isolated_and_restart_cancels_capture(self):
        g = self.game
        self.step(pygame.K_UP, 3)
        self.step(pygame.K_RIGHT, 4)
        self.step(pygame.K_DOWN, 3)
        grid = g.grid
        canvas = g.canvas
        before = [column[:] for column in grid]
        with mock.patch.object(upix, 'CAPTURE_MAX_CHUNKS', 1):
            for _ in range(10_000):
                g.advance_frame()
                if g._capture_grid and len(g._capture_grid) == upix.COLS:
                    break
            else:
                self.fail('Preparazione della griglia non raggiunta')
            g.advance_frame()  # Prima striscia preparata, nessun commit.
            self.assertIs(g.grid, grid)
            self.assertIs(g.canvas, canvas)
            self.assertEqual(g.grid, before)
            self.assertEqual(g.score, 0)
            self.assertIsNotNone(g._capture_canvas)
        with contextlib.redirect_stdout(io.StringIO()):
            g.start_level()
        self.assertEqual(g.state, GameState.PLAYING)
        self.assertIsNone(g._capture_work)
        self.assertIsNone(g._capture_canvas)
        self.assertEqual(g.score, 0)
        self.assertEqual(g.game_clock.ticks, 0)

    def test_level_profiles_select_assets_music_speed_and_equal_sprite_hitbox(self):
        for level in range(1, 13):
            g = self.game
            g.level = level
            with contextlib.redirect_stdout(io.StringIO()):
                g.start_level()
            self.assertEqual(g.level_config.boss_sprite, f'boss{level}.png')
            self.assertIn(g.music.current, g.music.shuffle.tracks)
            source = pygame.image.load(str(upix.ASSET_DIR / upix.MANIFEST['assets']['boss_dir'] /
                                           g.level_config.boss_sprite))
            width, height = g.boss_img.get_size()
            self.assertAlmostEqual(width / height, source.get_width() / source.get_height(), delta=0.025)
            self.assertLessEqual(width, round(g.level_config.boss_max_size[0] * g.level_config.boss_render_scale))
            self.assertLessEqual(height, round(g.level_config.boss_max_size[1] * g.level_config.boss_render_scale))
            self.assertEqual((g._boss_body().width, g._boss_body().height), (width, height))
            self.assertTrue(width == round(g.level_config.boss_max_size[0] * g.level_config.boss_render_scale)
                            or height == round(g.level_config.boss_max_size[1] * g.level_config.boss_render_scale))
            self.assertAlmostEqual(math.hypot(g.enemy_vx, g.enemy_vy), g.level_config.boss_speed)
            self.assertGreater(g.percent, 0)  # Bordo iniziale conteggiato subito.

    def test_all_twelve_levels_use_configured_shot_cadence_speed_and_target(self):
        g = self.game
        keys = collections.defaultdict(bool)
        for level in range(1, 13):
            with self.subTest(level=level):
                g.level = level
                with contextlib.redirect_stdout(io.StringIO()):
                    g.start_level()
                interval = g.level_config.missile_interval_ms
                for _ in range((interval * 60 + 999) // 1000 - 1):
                    g.update(keys)
                self.assertEqual(g.missiles, [])
                dx = g.player_x * upix.CELL_SIZE - g.enemy_x
                dy = g.player_y * upix.CELL_SIZE - g.enemy_y
                g.update(keys)
                self.assertEqual(g.last_shot_time, interval)
                self.assertEqual(len(g.missiles), 1)
                missile = g.missiles[0]
                self.assertAlmostEqual(math.hypot(missile['vx'], missile['vy']),
                                       g.level_config.missile_speed)
                self.assertAlmostEqual(missile['vx'] * dy - missile['vy'] * dx, 0)

    def test_aim_uses_current_logical_player_position_in_all_directions(self):
        g = self.game
        for x, y in ((250, 150), (150, 150), (200, 100), (200, 200), (280, 220)):
            g.missiles = []
            g.player_x, g.player_y = x, y
            g._shoot_at_player()
            missile = g.missiles[0]
            dx, dy = x * upix.CELL_SIZE - g.enemy_x, y * upix.CELL_SIZE - g.enemy_y
            self.assertAlmostEqual(missile['vx'] * dy - missile['vy'] * dx, 0)
            self.assertGreater(missile['vx'] * dx + missile['vy'] * dy, 0)
            self.assertAlmostEqual(math.hypot(missile['vx'], missile['vy']),
                                   g.level_config.missile_speed)
        g.missiles = []
        g.player_x, g.player_y = 200, 150
        g._shoot_at_player()
        self.assertEqual(g.missiles, [])

    def test_shock_counts_safe_movement_and_reduces_real_shot_interval(self):
        g = self.game
        g.shock = ShockSystem(ShockConfig(warning_ms=100, activation_ms=200))
        g.shoot_interval = 600
        keys = collections.defaultdict(bool, {pygame.K_RIGHT: True})
        for _ in range(11):
            g.update(keys)
        self.assertFalse(g.shock.active)
        self.assertTrue(g.shock.warning)
        g.update(keys)
        self.assertTrue(g.shock.active)
        self.assertEqual(g.player_x, upix.COLS // 2 + 12)
        for _ in range(5):
            g.update(keys)
        self.assertEqual(g.missiles, [])
        g.update(keys)
        self.assertEqual(g.last_shot_time, 300)
        self.assertEqual(len(g.missiles), 1)
        self.assertAlmostEqual(math.hypot(g.missiles[0]['vx'], g.missiles[0]['vy']),
                               g.level_config.missile_speed)
        self.step(pygame.K_UP, 3)
        self.assertTrue(g.drawing)
        g.update(collections.defaultdict(bool))
        self.assertTrue(g.shock.active)  # La partenza non neutralizza la pressione.
        g.handle_death()
        self.assertEqual(g.state, GameState.DYING)
        self.finish_death()
        self.assertFalse(g.shock.warning)
        self.assertEqual(g.shock.safe_ticks, 0)

    def test_capture_disarms_shock_and_hud_bonus_decays_with_level_time(self):
        g = self.game
        g.shock = ShockSystem(ShockConfig(warning_ms=0, activation_ms=100))
        for _ in range(6):
            g.update(collections.defaultdict(bool))
        self.assertTrue(g.shock.active)
        self.short_capture()
        self.assertEqual(g.shock.safe_ticks, 0)
        # Un taglio ampio produce un bonus ben visibile, soggetto al timer del livello.
        g.level_score.capture(12000)
        initial = g.hud_data()
        self.assertGreater(initial.bonus, 0)
        self.assertEqual(initial.score, g.level_score.base_points + initial.bonus)
        g.update(collections.defaultdict(bool))
        self.assertLess(g.hud_data().bonus, initial.bonus)
        g.game_clock.ticks = g.level_config.scoring.bonus_time_limit_ms * 60 // 1000
        self.assertEqual(g.hud_data().bonus, 0)
        self.assertEqual(g.score, g.level_score.base_points)
        with contextlib.redirect_stdout(io.StringIO()):
            g.next_level()
        self.assertEqual(g.score, 0)
        self.assertEqual(g.hud_data().bonus, 0)
        self.assertEqual(g.shock.safe_ticks, 0)

    def test_pause_capture_and_terminal_states_freeze_shock_and_score(self):
        g = self.game
        g.level_score.capture(12000)
        g.update(collections.defaultdict(bool))
        for state in (GameState.PAUSED, GameState.CAPTURING, GameState.LEVEL_CLEAR,
                      GameState.GAME_OVER, GameState.PHYSICS_ERROR):
            g._set_state(state)
            before = (g.shock.safe_ticks, g.score, g.hud_data().bonus, g.game_clock.ticks)
            self.now_ms += 120000
            g.update(collections.defaultdict(bool))
            g.draw()
            self.assertEqual(before, (g.shock.safe_ticks, g.score, g.hud_data().bonus,
                                      g.game_clock.ticks))

    def test_disabled_shock_preserves_base_cadence_in_runtime(self):
        g = self.game
        g.shock = ShockSystem(ShockConfig(enabled=False, warning_ms=0, activation_ms=100))
        g.shoot_interval = 600
        for _ in range(35):
            g.update(collections.defaultdict(bool))
        self.assertEqual(g.missiles, [])
        g.update(collections.defaultdict(bool))
        self.assertEqual(g.last_shot_time, 600)
        self.assertEqual(len(g.missiles), 1)
        self.assertFalse(g.shock.active)

    def test_player_sprite_is_centered_and_its_full_size_is_the_missile_hitbox(self):
        g = self.game
        source = pygame.image.load(str(upix.ASSET_DIR / upix.MANIFEST['assets']['player_sprite']))
        self.assertEqual(max(g.cursor_img.get_size()), max(upix.PLAYER_SPRITE_SIZE))
        self.assertAlmostEqual(g.cursor_img.get_width() / g.cursor_img.get_height(),
                               source.get_width() / source.get_height(), delta=1/30)
        g.player_x, g.player_y = 150, 150
        background = (17, 23, 31)
        g.canvas.fill(background)
        g.draw()
        bounds = g.cursor_img.get_rect(center=(301, 301))
        expected = pygame.Surface(g.cursor_img.get_size()).convert()
        expected.fill(background)
        expected.blit(g.cursor_img, (0, 0))
        self.assertEqual(pygame.image.tobytes(self.screen.subsurface(bounds), 'RGB'),
                         pygame.image.tobytes(expected, 'RGB'))
        g.drawing = True
        body = g._player_body()
        self.assertEqual((body.width, body.height), g.cursor_img.get_size())
        g.missiles = [{'x': body.right + upix.MISSILE_COLLISION_SIZE / 2 + 1,
                       'y': 301, 'vx': 0, 'vy': 0}]
        self.assertTrue(g._update_missiles())
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'])
        g.missiles = [{'x': body.right - 1, 'y': 301, 'vx': 0, 'vy': 0}]
        self.assertFalse(g._update_missiles())
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)

    def test_projectile_scale_updates_render_and_physical_body(self):
        body = self.game._missile_body({'x': 100, 'y': 100})
        self.assertAlmostEqual(body.width, 5.2)
        self.assertAlmostEqual(body.height, 5.2)
        self.assertEqual(upix.MISSILE_RENDER_RADIUS, 4)  # 3 * 1,3, arrotondato al pixel.

    def test_shock_spawns_visible_separate_threat_only_at_activation(self):
        g = self.game
        g.shock = ShockSystem(ShockConfig(warning_ms=100, activation_ms=200))
        keys = collections.defaultdict(bool)
        for _ in range(11):
            g.update(keys)
        self.assertTrue(g.shock.warning)
        self.assertIsNone(g.perimeter_threat)
        g.update(keys)
        self.assertIsInstance(g.perimeter_threat, PerimeterThreat)
        self.assertIsNotNone(g.threat_visual.image)
        self.assertIsNotNone(g.missile_visual.image)
        self.assertEqual(g.missiles, [])
        self.assertGreater(math.dist(g.perimeter_threat.position,
                                    (g.player_x * 2, g.player_y * 2)), 100)

    def test_perimeter_contact_on_safe_border_loses_one_life_and_disarms(self):
        g = self.game
        g.shock.safe_ticks = g.shock.config.activation_ms * 60 // 1000
        route = g.perimeter_routes[0]
        distance = route.project(((g.player_x + .5) * 2, (g.player_y + .5) * 2))[1]
        g.perimeter_threat = PerimeterThreat(route, distance, speed_per_tick=2.5, body_size=(10, 10))
        g.update(collections.defaultdict(bool))
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.assertEqual(g.state, GameState.DYING)
        self.finish_death()
        self.assertIsNone(g.perimeter_threat)
        self.assertFalse(g.shock.active)
        g.update(collections.defaultdict(bool))
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)

    def test_player_motion_into_threat_is_checked_in_same_tick(self):
        g = self.game
        route = g.perimeter_routes[0]
        target = (g._player_body().right + 1, (g.player_y + .5) * 2)
        g.perimeter_threat = PerimeterThreat(route, route.project(target)[1],
                                            speed_per_tick=1, body_size=(1, 4))
        self.assertFalse(g._player_touches_perimeter_threat())
        self.step(pygame.K_RIGHT)
        self.assertEqual(g.lives, upix.ENGINE['initial_lives'] - 1)
        self.finish_death()
        self.assertIsNone(g.perimeter_threat)

    def test_threat_freezes_on_pause_capture_and_terminal_states(self):
        g = self.game
        g.shock.safe_ticks = g.shock.config.activation_ms * 60 // 1000
        self.assertTrue(g._update_perimeter_threat())
        threat = g.perimeter_threat
        before = threat.distance, threat.velocity
        for state in (GameState.PAUSED, GameState.CAPTURING, GameState.LEVEL_CLEAR,
                      GameState.GAME_OVER, GameState.PHYSICS_ERROR):
            g._set_state(state)
            for _ in range(3):
                g.update(collections.defaultdict(bool))
                g.draw()
            self.assertEqual((threat.distance, threat.velocity), before)
        g._set_state(GameState.PLAYING)
        g.update(collections.defaultdict(bool))
        self.assertNotEqual(threat.distance, before[0])

    def test_capture_rebuilds_boundary_and_disarms_threat_atomically(self):
        g = self.game
        old_routes = g.perimeter_routes
        g.shock.safe_ticks = g.shock.config.activation_ms * 60 // 1000
        g._update_perimeter_threat()
        self.step(pygame.K_UP, 3)
        self.step(pygame.K_RIGHT, 4)
        self.step(pygame.K_DOWN, 3)
        self.assertEqual(g.state, GameState.CAPTURING)
        self.assertIs(g.perimeter_routes, old_routes)
        self.finish_capture()
        self.assertIsNone(g.perimeter_threat)
        self.assertFalse(g.shock.active)
        self.assertNotEqual(g.perimeter_routes, old_routes)
        self.assertEqual(len(g.perimeter_routes[0].vertices), 8)
        with contextlib.redirect_stdout(io.StringIO()):
            g.start_level()
        self.assertIsNone(g.perimeter_threat)
        self.assertEqual(len(g.perimeter_routes[0].vertices), 4)

    def test_shock_and_bonus_match_across_render_rates_after_activation(self):
        snapshots = []
        keys = collections.defaultdict(bool)
        for fps in (30, 60, 144):
            self.now_ms = 0
            with contextlib.redirect_stdout(io.StringIO()):
                g = upix.Game(self.screen, time_source=lambda: self.now_ms,
                              rng=random.Random(1989))
            g.shock = ShockSystem(ShockConfig(warning_ms=500, activation_ms=1000))
            g.level_score.capture(12000)
            try:
                for frame in range(1, fps * 4 + 1):
                    self.now_ms = frame * 1000 // fps
                    g.advance_frame(keys)
                    g.draw()
                self.assertTrue(g.shock.active)
                snapshots.append((g.game_clock.ticks, g.shock.safe_ticks, g.score,
                                  g.hud_data().bonus, g.last_shot_time, g.missiles,
                                  g.enemy_x, g.enemy_y, g.rng.getstate(),
                                  g.perimeter_threat.distance, g.perimeter_threat.velocity))
            finally:
                g._stop_draw_audio()
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])

    def test_level_three_pursuit_turns_toward_an_open_trail(self):
        g = self.game
        g.level = 3
        with contextlib.redirect_stdout(io.StringIO()):
            g.start_level()
        g.enemy_vx, g.enemy_vy = 0, g.level_config.boss_speed
        g.player_x, g.player_y = 300, 150
        g.drawing = True
        g.current_trail = [(300, 150)]
        interval = g.level_config.direction_interval_ms
        for _ in range((interval * 60 + 999) // 1000 - 1):
            g.game_clock.advance()
        with mock.patch.object(g.rng, 'uniform', return_value=0), \
                mock.patch.object(g, '_update_player'):
            g.update(collections.defaultdict(bool))
        self.assertGreater(g.enemy_vx, 0)
        self.assertGreater(g.enemy_vy, 0)
        self.assertAlmostEqual(math.hypot(g.enemy_vx, g.enemy_vy), g.level_config.boss_speed)
        self.assertEqual(g.enemy_change_dir_timer, interval)

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
        self.assertEqual(image.get_size(), (134, 98))
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
                        (icons / "boss1.png").write_bytes(b"invalid PNG")
                    with mock.patch.object(upix, "ASSET_DIR", Path(folder)):
                        with contextlib.redirect_stdout(io.StringIO()):
                            g = upix.Game(self.screen)
                    self.assertIsNone(g.boss_img)
                    self.assertEqual((g._boss_body().width, g._boss_body().height), (134, 98))
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


class MainLoopTests(unittest.TestCase):
    def test_main_projects_frame_and_handles_pause_focus_and_quit(self):
        now_ms = 0
        real_game = upix.Game
        real_present = upix.Viewport.present
        games, snapshots = [], []
        batches = iter([
            [], [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)], [],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)], [],
            [pygame.event.Event(pygame.WINDOWFOCUSLOST)], [],
            [pygame.event.Event(pygame.WINDOWFOCUSGAINED),
             pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q)],
        ])

        def build_game(screen, **kwargs):
            game = real_game(screen, time_source=lambda: now_ms, rng=random.Random(1989), **kwargs)
            games.append(game)
            return game

        def events():
            nonlocal now_ms
            now_ms += 17
            return next(batches)

        def present(viewport, overlay=None):
            real_present(viewport, overlay)
            if not games:
                snapshots.append((GameState.MENU, 0))
                return
            game = games[-1]
            snapshots.append((game.state, game.game_clock.ticks))
            self.assertEqual(pygame.display.get_surface().get_size(), (1024, 768))
            self.assertEqual(game.screen.get_size(), (800, 600))
            self.assertEqual(viewport.bounds, pygame.Rect(52, 66, 917, 688))
            self.assertEqual((game._boss_body().width, game._boss_body().height),
                             game.boss_img.get_size())

        with mock.patch.object(upix, 'Game', side_effect=build_game), \
                mock.patch('audio_normalization.prepare_configured_audio'), \
                mock.patch('application.MenuMusic') as menu_type, \
                mock.patch('pygame.event.get', side_effect=events), \
                mock.patch('pygame.time.Clock') as render_clock, \
                mock.patch.object(upix.Viewport, 'present', autospec=True, side_effect=present), \
                contextlib.redirect_stdout(io.StringIO()):
            menu_type.return_value.active = False  # La temporizzazione audio ha regressioni dedicate.
            upix.main()
        self.assertEqual(snapshots, [(GameState.MENU, 0), (GameState.PLAYING, 0),
                                    (GameState.PAUSED, 0), (GameState.PAUSED, 0),
                                    (GameState.PLAYING, 0), (GameState.PLAYING, 1),
                                    (GameState.PAUSED, 1), (GameState.PAUSED, 1)])
        self.assertEqual(render_clock.return_value.tick.call_count, 8)
        self.assertFalse(pygame.get_init())


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
