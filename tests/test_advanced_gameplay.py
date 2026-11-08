"""Integrazione delle ricompense con conquista atomica, fisica e campagna."""

import collections
import contextlib
from dataclasses import replace
import io
import os
import unittest
from unittest import mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from application import CampaignApp
from collisions import player_cell_allowed
from game_state import GameState
from shock_system import ShockSystem
from input_manager import InputFrame
from level_config import get_level_config
from manifest import MANIFEST
from music import MenuMusic
import Upqix89 as upix


class AdvancedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = upix.Game(self.screen)

    def tearDown(self):
        self.game._resume_audio()
        self.game._stop_draw_audio()
        pygame.mixer.music.stop()

    def finish_capture(self):
        for _ in range(5000):
            if self.game.state != GameState.CAPTURING:
                return
            self.game.advance_frame(InputFrame())
        self.fail('La cattura non termina')

    def test_five_initial_lives_inclusive_extra_life_and_no_duplicate_reward(self):
        game = self.game
        self.assertEqual(game.lives, 5)
        game.percent = 73.999
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertEqual(game.level_result.extra_life, 0)
        game.next_level()
        game.percent = 74
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertEqual(game.lives, 6)
        self.assertEqual(game.level_result.extra_life, 1)
        game._set_state(GameState.PLAYING)
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertEqual(game.lives, 6)

    def test_simulation_uses_supplied_input_without_reading_physical_devices(self):
        with mock.patch('pygame.key.get_pressed', side_effect=AssertionError('Hardware nel tick')):
            self.game.update(InputFrame())
            self.game.update()
        self.assertEqual(self.game.game_clock.ticks, 2)

    def test_large_single_capture_earns_shield_and_lands_on_new_frontier(self):
        game = self.game
        original = game.grid
        game.enemy_x, game.enemy_y = 600, 300
        for _ in range(upix.ROWS - 3):
            game._update_player(InputFrame((0, -1)))
        self.assertEqual(game.state, GameState.CAPTURING)
        self.assertEqual(game.shields.charges, 0)
        self.assertIs(game.grid, original)
        self.finish_capture()
        self.assertEqual(game.state, GameState.PLAYING)
        self.assertGreater(game.percent, 25)
        self.assertEqual(game.shields.charges, 1)
        self.assertEqual(game.hud_data().shields, 1)
        self.assertTrue(player_cell_allowed(game.collision_grid, game.player_x, game.player_y))
        self.assertEqual(game.grid[game.player_x][game.player_y], upix.FILLED)
        self.assertEqual((game.player_x, game.player_y), (game.last_safe_x, game.last_safe_y))
        game.draw()
        self.assertIsNotNone(game.shield_notice_img)

    def test_equipped_shield_absorbs_projectile_once_without_partial_capture(self):
        game = self.game
        game.shields.award(25, 100)
        game.request_shield()
        game.update(InputFrame())
        self.assertTrue(game.shields.active)
        game.player_x, game.player_y = 100, 100
        game.drawing = True
        game.current_trail = [(100, 101), (100, 100)]
        grid = [column.copy() for column in game.grid]
        game.missiles = [{'x':201, 'y':201, 'vx':1, 'vy':0}]
        self.assertFalse(game._update_missiles())
        self.assertEqual(game.lives, 5)
        self.assertEqual(game.shields.charges, 0)
        self.assertFalse(game.shields.active)
        self.assertFalse(game.drawing)
        self.assertEqual(game.current_trail, [])
        self.assertEqual(game.grid, grid)
        self.assertEqual(game.missiles, [])
        game._handle_hostile_contact()
        self.assertEqual(game.lives, 5)
        for _ in range(30): game.shields.advance()
        game._handle_hostile_contact()
        self.assertEqual(game.lives, 4)

    def test_two_shocks_keep_opposite_directions_from_level_five(self):
        game = self.game
        game.level = 5
        with contextlib.redirect_stdout(io.StringIO()): game.start_level()
        game.shock.safe_ticks = (game.shock.config.activation_ms * 60 + 999) // 1000
        game._update_perimeter_threat()
        first, second = game.perimeter_threats
        self.assertEqual((first.fixed_direction, second.fixed_direction), (1, -1))
        before = first.distance, second.distance
        game._update_perimeter_threat()
        self.assertAlmostEqual((first.distance - before[0]) % first.route.length, first.speed_per_tick)
        self.assertAlmostEqual((before[1] - second.distance) % second.route.length, second.speed_per_tick)
        self.assertGreater(get_level_config(5).perimeter_speed_px_per_second,
                           get_level_config(4).perimeter_speed_px_per_second)
        self.assertLess(get_level_config(5).shock.activation_ms, get_level_config(4).shock.activation_ms)

    def test_cycle_preserves_run_inventory_and_lives_but_resets_level_state(self):
        game = self.game
        game.level = 12
        with contextlib.redirect_stdout(io.StringIO()): game.start_level()
        game.shields.charges = 2
        game.level_score.capture(100)
        game.percent = 90
        game._set_state(GameState.LEVEL_CLEAR)
        points, lives = game.run_score, game.lives
        game.next_level()
        self.assertEqual(game.state, GameState.CAMPAIGN_COMPLETE)
        with contextlib.redirect_stdout(io.StringIO()): game.continue_cycle()
        self.assertEqual((game.level, game.cycle, game.lives), (1, 2, lives))
        self.assertEqual(game.run_score, points)
        self.assertEqual(game.shields.charges, 2)
        self.assertEqual(game.game_clock.ticks, 0)
        self.assertEqual(game.score, 0)
        self.assertFalse(game.shock.warning)
        self.assertEqual(game.missiles, [])
        self.assertGreater(game.level_config.boss_speed, get_level_config(1).boss_speed)
        game.percent = 80
        game.level_score.capture(200)
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertEqual(len(game.run.results), 2)
        self.assertEqual(game.run.results[-1].cycle, 2)
        self.assertGreater(game.run_score, points)

    def test_loop_limits_and_twelve_distinct_assets(self):
        for level in range(1, 13):
            self.assertEqual(get_level_config(level).boss_sprite, f'boss{level}.png')
            extreme = get_level_config(level, 10000)
            base = get_level_config(level)
            self.assertLessEqual(extreme.boss_speed, base.boss_speed * 2)
            self.assertGreaterEqual(extreme.shock.activation_ms, 3000)
            self.assertLessEqual(extreme.victory_percent, 90)
            self.assertGreaterEqual(extreme.missile_interval_ms, 300)

    def test_tutorial_and_shield_action_are_routed_through_application(self):
        menu_music = MenuMusic(upix.ASSET_DIR / MANIFEST['assets']['menu_music'],
                               volume=.26, fade_in_ms=0, fade_out_ms=0)
        app = CampaignApp(self.screen, lambda surface, **kwargs: self.game, menu_music=menu_music)
        try:
            for _ in range(2):
                app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.assertEqual(app.state, GameState.TUTORIAL)
            app.draw()
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            app.selected = 0
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.game.shields.charges = 1
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            self.assertFalse(self.game.shields.active)
            self.game.update(InputFrame())
            self.assertTrue(self.game.shields.active)
        finally:
            app.close()

    def test_two_shocks_and_shield_contact_match_at_30_60_144_fps(self):
        import random
        snapshots = []
        for fps in (30, 60, 144):
            now = 0
            with contextlib.redirect_stdout(io.StringIO()):
                game = upix.Game(self.screen, time_source=lambda: now, rng=random.Random(1989))
                game.level = 5
                game.start_level()
            try:
                game.shock = ShockSystem(replace(game.level_config.shock, warning_ms=100, activation_ms=500))
                game.shields.charges = 1
                game.request_shield()
                for frame in range(1, fps * 9 + 1):
                    now = frame * 1000 // fps
                    game.advance_frame(InputFrame())
                    game.draw()
                self.assertEqual(game.lives, 5)
                self.assertEqual(game.shields.charges, 0)
                self.assertFalse(game.shields.active)
                snapshots.append((game.game_clock.ticks, game.lives, game.score,
                    game.shields.grace_ticks, game.enemy_x, game.enemy_y, game.missiles,
                    tuple((t.distance, t.direction, t.velocity) for t in game.perimeter_threats),
                    game.rng.getstate()))
            finally:
                game._stop_draw_audio()
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])
