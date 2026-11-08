"""Run Score, menu iniziale e salvataggio tramite il percorso utente reale."""

import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from application import CampaignApp
from campaign import LevelResult, RunScore
from game_state import GameState
from highscores import JsonScoreStore
from highscores import ScoreStoreError
from Upqix89 import Game
from debug_menu import StartSettings
from input_manager import InputFrame
from localization import I18N
from manifest import MANIFEST, MANIFEST_PATH


class RunScoreTests(unittest.TestCase):
    def test_same_level_in_next_cycle_is_a_new_result_and_totals_remain_idempotent(self):
        run = RunScore()
        run.complete(LevelResult(1, 100, 20, 1000, 80, 5))
        second = LevelResult(1, 200, 30, 2000, 85, 6, cycle=2)
        run.complete(second)
        run.complete(second)
        self.assertEqual(run.banked, 350)
        self.assertEqual(run.elapsed_ms, 3000)
        self.assertEqual(run.completed_count, 2)
        self.assertEqual(run.total(1, 230, cycle=2), 350)
        self.assertEqual(run.total(1, 50, cycle=3), 400)

    def test_completed_bonus_is_banked_once_and_current_level_is_not_counted_twice(self):
        run = RunScore()
        first = LevelResult(1, 1000, 200, 1500, 75, 3)
        self.assertEqual(run.complete(first), first)
        run.complete(LevelResult(1, 9999, 9999, 9999, 99, 3))
        self.assertEqual(run.total(1, 1200), 1200)
        self.assertEqual(run.total(2, 400), 1600)
        run.complete(LevelResult(2, 400, 100, 2500, 80, 2))
        self.assertEqual(run.banked, 1700)
        self.assertEqual(run.total(2, 500), 1700)
        self.assertEqual(run.elapsed_ms, 4000)


class CampaignAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'highscores.json'
        self.now = 0

        def factory(surface, **kwargs):
            with contextlib.redirect_stdout(io.StringIO()):
                return Game(surface, time_source=lambda: self.now, **kwargs)

        self.factory = mock.Mock(side_effect=factory)
        self.app = CampaignApp(self.surface, self.factory, store=JsonScoreStore(self.path))

    def tearDown(self):
        self.app.close()
        self.folder.cleanup()

    def press(self, key):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def start(self):
        self.press(pygame.K_RETURN)
        return self.app.game

    def continue_level(self):
        if self.app.game.level_rewards_pending:
            self.press(pygame.K_RETURN)
        self.press(pygame.K_RETURN)

    def finish_death(self):
        for _ in range(100):
            if self.app.game.state != GameState.DYING:
                return
            self.now += 17
            self.app.advance(InputFrame())
        self.fail('La sequenza di morte non termina')

    def test_boot_is_menu_and_arrow_navigation_does_not_start_simulation(self):
        self.assertEqual(self.app.state, GameState.MENU)
        self.app.advance()
        self.app.draw()
        self.factory.assert_not_called()
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.HIGHSCORES)
        self.factory.assert_not_called()
        self.assertFalse(self.path.exists())
        self.press(pygame.K_ESCAPE)
        self.press(pygame.K_UP)
        self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.PLAYING)

    def test_summary_freezes_score_and_total_survives_next_level(self):
        game = self.start()
        game.level_score.capture(12000)
        game.percent = 75
        game._set_state(GameState.LEVEL_CLEAR)
        first = game.score
        self.app.draw()
        self.assertEqual(game.level_result.score, first)
        self.assertEqual(game.run_score, first)
        self.now += 120000
        self.app.advance()
        self.assertEqual(game.run_score, first)
        self.continue_level()
        self.assertEqual(game.level, 2)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.run_score, first)
        game.level_score.capture(1000)
        self.assertEqual(game.hud_data().score, first + game.score)
        self.assertEqual(game.game_clock.ticks, 0)

    def test_game_over_name_entry_writes_json_and_can_be_reloaded(self):
        game = self.start()
        game.level_score.capture(1000)
        expected = game.run_score
        game.lives = 1
        game.handle_death()
        self.assertEqual(self.app.state, GameState.DYING)
        self.finish_death()
        self.app.advance()
        self.assertEqual(self.app.state, GameState.NAME_ENTRY)
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Lukso'))
        self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.HIGHSCORES)
        entries = JsonScoreStore(self.path).load()
        self.assertEqual(len(entries), 1)
        self.assertEqual((entries[0].name, entries[0].score), ('Lukso', expected))
        self.assertFalse(entries[0].completed)

    def test_entire_campaign_finishes_without_restarting_level_one(self):
        game = self.start()
        expected = 0
        for level in range(1, game.max_levels + 1):
            game.level_score.capture(100)
            game.percent = 90
            game._set_state(GameState.LEVEL_CLEAR)
            expected += game.score
            self.assertEqual(game.run_score, expected)
            self.continue_level()
        self.app.advance()
        self.assertEqual(self.app.state, GameState.CAMPAIGN_COMPLETE)
        self.assertEqual(game.level, game.max_levels)
        self.assertEqual(len(game.run.results), 12)
        self.assertEqual(game.run_score, expected)
        self.press(pygame.K_DOWN)  # Registra e termina; default: nuovo ciclo.
        self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.NAME_ENTRY)
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Campione'))
        self.press(pygame.K_RETURN)
        self.assertTrue(JsonScoreStore(self.path).load()[0].completed)

    def test_save_failure_keeps_name_and_allows_retry_without_duplicate(self):
        game = self.start()
        game._set_state(GameState.GAME_OVER)
        self.app.advance()
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Player'))
        with mock.patch('highscores.os.replace', side_effect=PermissionError('busy')):
            self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.NAME_ENTRY)
        self.assertEqual(self.app.name, 'Player')
        self.assertTrue(self.app.message)
        self.press(pygame.K_RETURN)
        self.assertEqual(len(JsonScoreStore(self.path).load()), 1)

    def test_continuing_cycle_and_game_over_save_all_thirteen_level_results(self):
        game = self.start()
        for _ in range(12):
            game.level_score.capture(100)
            game.percent = 90
            game._set_state(GameState.LEVEL_CLEAR)
            self.continue_level()
        self.app.advance()
        self.press(pygame.K_RETURN)  # Continua ciclo 2.
        self.assertEqual((game.level, game.cycle), (1, 2))
        game.level_score.capture(200)
        game.percent = 80
        game._set_state(GameState.LEVEL_CLEAR)
        total = game.run_score
        self.continue_level()
        game.lives = 1
        game.handle_death()
        self.finish_death()
        self.app.advance()
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Looper'))
        self.press(pygame.K_RETURN)
        entry = JsonScoreStore(self.path).load()[0]
        self.assertEqual(entry.levels_completed, 13)
        self.assertEqual(entry.score, total)
        self.assertTrue(entry.completed)

    def test_unreadable_leaderboard_can_retry_without_leaving_the_screen(self):
        self.press(pygame.K_DOWN)
        with mock.patch.object(self.app.store, 'load', side_effect=ScoreStoreError('offline')):
            self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.HIGHSCORES)
        self.assertTrue(self.app.message)
        self.press(pygame.K_RETURN)
        self.assertEqual(self.app.state, GameState.HIGHSCORES)
        self.assertFalse(self.app._scores_failed)
        self.assertEqual(self.app.entries, [])

    def enter_cheat(self):
        for key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                    pygame.K_UP, pygame.K_UP, pygame.K_SPACE):
            self.press(key)

    def test_debug_sequence_opens_overlay_and_starts_with_ephemeral_values(self):
        before = MANIFEST_PATH.read_bytes()
        self.enter_cheat()
        self.assertEqual(self.app.state, GameState.DEBUG_MENU)
        self.factory.assert_not_called()
        self.app.draw()
        for _ in range(11): self.press(pygame.K_RIGHT)
        self.press(pygame.K_DOWN)
        for _ in range(2): self.press(pygame.K_RIGHT)
        self.press(pygame.K_DOWN)
        for _ in range(3): self.press(pygame.K_RIGHT)
        self.press(pygame.K_RETURN)
        game = self.app.game
        self.assertEqual((game.level, game.lives, game.shields.charges), (12, 7, 3))
        self.assertEqual(game.cycle, 1)
        self.assertIs(game.music, self.app.music)
        self.app._menu()
        self.app.selected = 0
        self.press(pygame.K_RETURN)
        self.assertEqual((self.app.game.level, self.app.game.lives, self.app.game.shields.charges), (1, 5, 0))
        self.app.close()
        self.assertEqual(self.app.debug_settings, StartSettings())
        self.assertEqual(MANIFEST_PATH.read_bytes(), before)

    def test_sequence_is_menu_only_and_focus_loss_discards_a_partial_code(self):
        self.app.selected = 2
        self.press(pygame.K_RETURN)
        self.enter_cheat()
        self.assertEqual(self.app.state, GameState.TUTORIAL)
        self.press(pygame.K_ESCAPE)
        self.press(pygame.K_UP)
        self.press(pygame.K_DOWN)
        self.app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        for key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_UP, pygame.K_SPACE):
            self.press(key)
        self.assertEqual(self.app.state, GameState.MENU)
        self.enter_cheat()
        self.assertEqual(self.app.state, GameState.DEBUG_MENU)

    def test_debug_fifteen_lives_reaches_name_entry_only_after_fifteen_deaths(self):
        self.enter_cheat()
        self.press(pygame.K_DOWN)
        for _ in range(10):
            self.press(pygame.K_RIGHT)
        self.press(pygame.K_RETURN)
        game = self.app.game
        self.assertEqual(game.lives, 15)
        for death in range(1, 16):
            with contextlib.redirect_stdout(io.StringIO()):
                game.handle_death()
            self.assertEqual(self.app.state, GameState.DYING)
            self.finish_death()
            self.app.advance(InputFrame())
            self.assertEqual(self.app.hud_data().lives, 15 - death)
            self.assertEqual(self.app.state, GameState.PLAYING if death < 15 else GameState.NAME_ENTRY)
        self.assertTrue(game.game_over)
        self.assertEqual(game.lives, 0)
        self.app.draw()

    def test_menu_cancels_explosion_and_next_run_has_no_pending_death(self):
        game = self.start()
        with contextlib.redirect_stdout(io.StringIO()):
            game.handle_death()
        self.assertEqual(self.app.state, GameState.DYING)
        self.app._menu()
        self.assertFalse(game.death_sequence.active)
        self.assertFalse(game.death_channel.get_busy())
        replacement = self.start()
        self.assertEqual(replacement.state, GameState.PLAYING)
        self.assertFalse(replacement.death_sequence.active)
        self.assertEqual(replacement.lives, MANIFEST['engine']['initial_lives'])

    def test_language_menu_switches_immediately_without_starting_the_game(self):
        original = I18N.language
        try:
            self.app.selected = MANIFEST['ui']['menu_actions'].index('language')
            self.press(pygame.K_RETURN)
            self.assertNotEqual(I18N.language, original)
            with mock.patch.object(self.app.renderer, 'draw') as draw:
                self.app.draw()
                self.assertEqual(draw.call_args.args[1], I18N['menu_items'])
            self.factory.assert_not_called()
            self.press(pygame.K_RETURN)
            self.assertEqual(I18N.language, original)
        finally:
            I18N.set_language(original)

    def test_life_and_shield_rewards_are_both_visible_even_when_earned_earlier(self):
        game = self.start()
        game.shields.earned_this_level = 1
        game.shields.notice_ticks = 0  # Il premio scudo era già apparso durante il livello.
        game.percent = 74
        game._set_state(GameState.LEVEL_CLEAR)
        self.assertTrue(game.level_rewards_pending)
        game.life_notice_img = pygame.Surface((30, 30))
        game.life_notice_img.fill((210, 10, 20))
        game.shield_notice_img = pygame.Surface((30, 30))
        game.shield_notice_img.fill((10, 20, 210))
        before = game.lives, game.shields.charges, game.run_score
        self.app.draw()
        self.assertEqual(self.surface.get_at((400, 230))[:3], (210, 10, 20))
        self.assertEqual(self.surface.get_at((400, 370))[:3], (10, 20, 210))
        self.assertEqual((game.lives, game.shields.charges, game.run_score), before)
        self.press(pygame.K_RETURN)
        self.assertFalse(game.level_rewards_pending)
        self.assertEqual(game.level, 1)
        self.press(pygame.K_RETURN)
        self.assertEqual(game.level, 2)
