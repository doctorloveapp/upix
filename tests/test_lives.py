"""Contabilità vite e respawn con collisioni reali e tempo controllato."""

import collections
import contextlib
from dataclasses import replace
import io
import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from debug_menu import StartSettings
from game_state import GameState
from input_manager import InputFrame
import Upqix89 as upix


class LivesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.now = 0
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.game = upix.Game(self.surface, time_source=lambda: self.now,
                              start_options=StartSettings(lives=15))
        # Boss valido, tangente al bordo inferiore; colpisce solo tentando il taglio.
        self.game.enemy_x = self.game.player_x * upix.CELL_SIZE + .5 * upix.CELL_SIZE
        self.game.enemy_y = ((upix.ROWS - upix.ENGINE['border_cells']) * upix.CELL_SIZE
                             - self.game.boss_size[1] / 2)
        self.game.enemy_vx = self.game.enemy_vy = 0
        self.game.level_config = replace(self.game.level_config, direction_interval_ms=1_000_000)
        self.game.shoot_interval = None

    def tearDown(self):
        self.game._resume_audio()
        self.game._stop_draw_audio()
        pygame.mixer.music.stop()
        self.output.__exit__(None, None, None)

    def collide(self):
        self.game._update_player(InputFrame())  # Rilascio: nuovo tentativo intenzionale.
        self.game._update_player(InputFrame((0, -1)))
        self.finish_death()

    def finish_death(self, game=None):
        game = game or self.game
        for _ in range(100):
            if game.state != GameState.DYING:
                return
            self.now += 17
            game.advance_frame(InputFrame((0, -1)))
        self.fail('La sequenza di morte non termina')

    def test_fifteen_lives_ten_distinct_collisions_leave_five_and_fifteenth_ends_run(self):
        game = self.game
        self.assertEqual(game.lives, 15)
        for death in range(1, 16):
            self.collide()
            self.assertEqual(game.lives, 15 - death)
            self.assertEqual(game.hud_data().lives, 15 - death)
            self.assertEqual(game.state, GameState.PLAYING if death < 15 else GameState.GAME_OVER)
        for _ in range(10):
            game.handle_death()
            game.update(InputFrame((0, -1)))
        self.assertEqual(game.lives, 0)

    def test_death_interrupts_catchup_before_another_invisible_loss(self):
        self.now = 100  # Sei tick dovuti prima del prossimo rendering.
        self.assertEqual(self.game.advance_frame(InputFrame((0, -1))), 1)
        self.assertEqual(self.game.lives, 14)
        self.assertEqual(self.game.game_clock.ticks, 1)
        self.assertEqual(self.game.advance_frame(InputFrame((0, -1))), 0)

    def test_held_direction_cannot_restart_cut_until_neutral_input(self):
        self.collide()
        game = self.game
        spawn = game.player_x, game.player_y
        for direction in ((0, -1), (1, 0), (0, -1)):
            for _ in range(20):
                game.update(InputFrame(direction))
        self.assertEqual(game.lives, 14)
        self.assertEqual((game.player_x, game.player_y), spawn)
        self.assertFalse(game.drawing)
        self.assertFalse(game.draw_channel.get_busy())
        self.assertGreater(game.game_clock.ticks, 0)  # Il mondo non è in pausa.
        game.update(InputFrame())
        game.update(InputFrame((0, -1)))
        self.assertEqual(game.lives, 13)

    def test_keyboard_mapping_requires_release_too(self):
        keys = collections.defaultdict(bool, {pygame.K_UP: True})
        self.game._update_player(keys)
        self.finish_death()
        self.game._update_player(keys)
        self.assertEqual(self.game.lives, 14)
        self.game._update_player(collections.defaultdict(bool))
        self.game._update_player(keys)
        self.assertEqual(self.game.lives, 13)

    def test_level_reward_is_added_once_and_next_level_keeps_remaining_lives(self):
        for _ in range(10):
            self.collide()
        game = self.game
        game.percent = 74
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertEqual(game.lives, 6)
        game._set_state(GameState.PLAYING)
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertEqual(game.lives, 6)
        game.next_level()
        self.assertEqual(game.lives, 6)
        self.assertEqual(game.state, GameState.PLAYING)
        spawn_x = game.player_x
        game._update_player(InputFrame((1, 0)))
        self.assertEqual(game.player_x, spawn_x + 1)
        self.assertEqual(game.dx, 1)

    def test_armed_shield_is_separate_from_life_counter(self):
        game = self.game
        game.shields.charges = 5
        game.shields.activate()
        self.collide()
        self.assertEqual((game.lives, game.shields.charges), (15, 4))
        for _ in range(game.shields.grace_ticks):
            game.shields.advance()
        self.collide()
        self.assertEqual((game.lives, game.shields.charges), (14, 4))

    def test_nonplaying_states_cannot_consume_lives(self):
        for state in (GameState.PAUSED, GameState.DYING, GameState.CAPTURING, GameState.LEVEL_CLEAR,
                      GameState.CAMPAIGN_COMPLETE, GameState.GAME_OVER, GameState.PHYSICS_ERROR):
            self.game._set_state(state)
            self.game.shields.charges = 2
            self.game.shields.active = True
            lives = self.game.lives
            self.game.handle_death()
            self.game._handle_hostile_contact()
            self.assertEqual(self.game.lives, lives)
            self.assertEqual(self.game.shields.charges, 2)

    def test_pause_does_not_rearm_held_direction_after_respawn(self):
        self.collide()
        self.game.toggle_pause()
        self.game.update(InputFrame())
        self.game.toggle_pause()
        self.game.update(InputFrame((0, -1)))
        self.assertEqual(self.game.lives, 14)
        self.game.update(InputFrame())
        self.game.update(InputFrame((0, -1)))
        self.assertEqual(self.game.lives, 13)

    def test_waiting_for_release_does_not_disable_perimeter_threat(self):
        from perimeter_threat import PerimeterThreat

        self.collide()
        game = self.game
        game.shock.safe_ticks = game.shock.config.activation_ms * 60 // 1000
        route = game.perimeter_routes[0]
        target = ((game.player_x + .5) * upix.CELL_SIZE,
                  (game.player_y + .5) * upix.CELL_SIZE)
        distance = route.project(target)[1]
        game.perimeter_threat = PerimeterThreat(route, distance, speed_per_tick=1, body_size=(10, 10))
        game.update(InputFrame((0, -1)))
        self.assertEqual(game.lives, 13)
        self.assertEqual(game.state, GameState.DYING)
        self.finish_death()
        self.assertIsNone(game.perimeter_threat)

    def test_maximum_debug_lives_are_not_capped_to_normal_start_value(self):
        game = upix.Game(self.surface, time_source=lambda: self.now,
                         start_options=StartSettings(lives=99))
        self.addCleanup(game._stop_draw_audio)
        for death in range(1, 100):
            game.handle_death()
            self.finish_death(game)
            self.assertEqual(game.lives, 99 - death)
            self.assertEqual(game.state, GameState.PLAYING if death < 99 else GameState.GAME_OVER)

    def test_held_input_loses_only_one_life_at_different_render_rates(self):
        game = self.game
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                self.now = 0
                game.lives = 15
                game.frame_clock = upix.FixedTimestep(lambda: self.now)
                game._respawn_waiting_for_release = False
                for frame in range(1, fps + 1):
                    self.now = frame * 1000 // fps
                    game.advance_frame(InputFrame((0, -1)))
                self.assertEqual(game.lives, 14)
                self.assertEqual(game.state, GameState.PLAYING)


if __name__ == '__main__':
    unittest.main()
