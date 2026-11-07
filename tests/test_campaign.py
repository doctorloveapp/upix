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


class RunScoreTests(unittest.TestCase):
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

        def factory(surface):
            with contextlib.redirect_stdout(io.StringIO()):
                return Game(surface, time_source=lambda: self.now)

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
        self.press(pygame.K_RETURN)
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
            self.press(pygame.K_RETURN)
        self.app.advance()
        self.assertEqual(self.app.state, GameState.CAMPAIGN_COMPLETE)
        self.assertEqual(game.level, game.max_levels)
        self.assertEqual(len(game.run.results), 12)
        self.assertEqual(game.run_score, expected)
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
