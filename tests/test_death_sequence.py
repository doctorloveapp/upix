"""Durata, congelamento e commit unico della morte, senza attese reali."""

import contextlib
import io
import os
import random
import tempfile
import unittest
from unittest import mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from assets import load_animation_frames
from death_sequence import DeathSequence
from game_state import GameState
from input_manager import InputFrame
from manifest import MANIFEST, ROOT
import Upqix89 as upix


class DeathSequenceTests(unittest.TestCase):
    def test_all_seven_frames_keep_their_full_duration_and_finish_once(self):
        sequence = DeathSequence(7, 100, 60)
        sequence.start((201, 303))
        self.assertEqual(sequence.center, (201, 303))
        for tick in range(42):
            self.assertTrue(sequence.active)
            self.assertEqual(sequence.frame_index, tick // 6)
            self.assertEqual(sequence.advance(), tick == 41)
        self.assertFalse(sequence.active)
        self.assertFalse(sequence.advance())
        self.assertEqual(sequence.elapsed_ticks, 42)

    def test_cancel_and_restart_have_no_previous_animation_credit(self):
        sequence = DeathSequence(7, 101, 60)
        self.assertEqual(sequence.ticks_per_frame, 7)
        sequence.start((1, 2))
        sequence.advance()
        sequence.cancel()
        self.assertIsNone(sequence.center)
        self.assertFalse(sequence.advance())
        sequence.start((4, 5))
        self.assertEqual((sequence.elapsed_ticks, sequence.frame_index), (0, 0))


class DeathIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.now = 0
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = upix.Game(self.surface, time_source=lambda: self.now)

    def tearDown(self):
        self.game.cancel_death()
        self.game._resume_audio()
        self.game._stop_draw_audio()
        pygame.mixer.music.stop()

    def begin(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.game.handle_death()

    def advance_until(self, milliseconds):
        while self.now < milliseconds:
            self.now = min(milliseconds, self.now + 10)
            self.game.advance_frame(InputFrame((0, -1)))

    def test_animation_and_audio_begin_before_single_life_decrement(self):
        game = self.game
        lives = game.lives
        channel = mock.Mock()

        def on_play(sound):
            self.assertIs(sound, game.death_sound)
            self.assertEqual(game.state, GameState.DYING)
            self.assertTrue(game.death_sequence.active)
            self.assertEqual(game.death_sequence.frame_index, 0)
            self.assertEqual(game.lives, lives)

        channel.play.side_effect = on_play
        with mock.patch.object(game, 'death_channel', channel):
            self.begin()
            for _ in range(10):
                game.handle_death()
                game._handle_hostile_contact()
                game.draw()
            self.assertEqual(game.lives, lives - 1)
            channel.play.assert_called_once_with(game.death_sound)

    def test_world_score_timer_and_input_freeze_until_last_frame_expires(self):
        game = self.game
        game._update_player(InputFrame((0, -1)))
        game.missiles = [{'x': 100, 'y': 100, 'vx': 2, 'vy': 1}]
        game.level_score.capture(1000)
        self.begin()
        snapshot = (game.enemy_x, game.enemy_y, game.player_x, game.player_y,
                    list(game.current_trail), [dict(m) for m in game.missiles],
                    game.shock.safe_ticks, game.shields.grace_ticks,
                    game.game_clock.ticks, game.run_score, game.rng.getstate())
        for _ in range(20):
            game.update(InputFrame((1, 0)))
            game.request_shield()
        self.advance_until(699)
        self.assertEqual(game.state, GameState.DYING)
        self.assertEqual(game.death_sequence.frame_index, 6)
        self.assertEqual(snapshot, (
            game.enemy_x, game.enemy_y, game.player_x, game.player_y,
            game.current_trail, game.missiles, game.shock.safe_ticks, game.shields.grace_ticks,
            game.game_clock.ticks, game.run_score, game.rng.getstate()))
        self.advance_until(700)
        self.assertEqual(game.state, GameState.PLAYING)
        self.assertEqual(game.game_clock.ticks, snapshot[8])
        self.assertEqual(game.missiles, [])
        self.assertEqual(game.current_trail, [])
        self.assertEqual((game.player_x, game.player_y), (game.last_safe_x, game.last_safe_y))
        self.assertEqual(game.advance_frame(InputFrame()), 0)
        self.now += 17
        self.assertEqual(game.advance_frame(InputFrame()), 1)
        self.assertEqual(game.game_clock.ticks, snapshot[8] + 1)

    def test_zero_lives_waits_for_entire_sequence_before_game_over(self):
        self.game.lives = 1
        self.begin()
        self.assertEqual(self.game.lives, 0)
        self.assertFalse(self.game.game_over)
        self.advance_until(699)
        self.assertEqual(self.game.state, GameState.DYING)
        self.advance_until(700)
        self.assertTrue(self.game.game_over)
        self.game.handle_death()
        self.assertEqual(self.game.lives, 0)

    def test_pause_and_focus_style_suspend_explosion_without_replaying_audio(self):
        with mock.patch.object(self.game, 'death_channel', wraps=self.game.death_channel) as channel:
            self.begin()
            self.advance_until(200)
            ticks = self.game.death_sequence.elapsed_ticks
            self.game.pause()
            self.advance_until(10000)
            self.assertEqual(self.game.death_sequence.elapsed_ticks, ticks)
            self.game.toggle_pause()
            self.assertEqual(self.game.state, GameState.DYING)
            self.advance_until(10499)
            self.assertEqual(self.game.state, GameState.DYING)
            self.advance_until(10500)
            self.assertEqual(self.game.state, GameState.PLAYING)
            channel.play.assert_called_once()

    def test_assets_share_scale_preserve_growth_and_render_at_impact_center(self):
        game = self.game
        sources = [pygame.image.load(str(ROOT / 'public' / path))
                   for path in MANIFEST['assets']['death_frames']]
        scale = min(game.player_sprite_size[0] / sources[0].get_width(),
                    game.player_sprite_size[1] / sources[0].get_height())
        for source, frame in zip(sources, game.death_frames):
            self.assertEqual(frame.get_size(), tuple(max(1, round(n * scale)) for n in source.get_size()))
        game.player_x, game.player_y = 120, 130
        self.begin()
        center = (241, 261)
        self.assertEqual(game.death_sequence.center, center)
        color = (255, 240, 10)
        game.death_frames = tuple(pygame.Surface(frame.get_size()) for frame in game.death_frames)
        for frame in game.death_frames:
            frame.fill(color)
        for index in range(7):
            game.death_sequence.elapsed_ticks = index * game.death_sequence.ticks_per_frame
            game.draw()
            bounds = game.death_frames[index].get_rect(center=center)
            self.assertEqual(self.surface.get_at(bounds.topleft)[:3], color)
            self.assertEqual(self.surface.get_at((bounds.right - 1, bounds.bottom - 1))[:3], color)
            self.assertEqual(game.death_sequence.center, center)

    def test_missing_animation_and_audio_do_not_skip_timing_or_crash(self):
        game = self.game
        game.death_frames = (None,) * 7
        game.death_sound = None
        self.begin()
        game.draw()
        self.advance_until(699)
        self.assertEqual(game.state, GameState.DYING)
        self.advance_until(700)
        self.assertEqual(game.state, GameState.PLAYING)

    def test_new_level_cancels_explosion_and_resets_presentation_clock(self):
        self.begin()
        self.advance_until(200)
        with contextlib.redirect_stdout(io.StringIO()):
            self.game.start_level()
        self.assertFalse(self.game.death_sequence.active)
        self.assertIsNone(self.game.death_sequence.center)
        self.assertEqual(self.game.advance_frame(InputFrame()), 0)

    def test_death_timing_and_frozen_simulation_match_at_30_60_144_fps(self):
        snapshots = []
        for fps in (30, 60, 144):
            now = 0
            with contextlib.redirect_stdout(io.StringIO()):
                game = upix.Game(self.surface, time_source=lambda: now, rng=random.Random(1989))
                game.handle_death()
            try:
                seen = {game.death_sequence.frame_index}
                for frame in range(1, fps + 1):
                    now = min(700, frame * 1000 // fps)
                    game.advance_frame(InputFrame((0, -1)))
                    game.draw()
                    if now < 700:
                        self.assertEqual(game.state, GameState.DYING)
                        seen.add(game.death_sequence.frame_index)
                    else:
                        break
                self.assertEqual(seen, set(range(7)))
                self.assertEqual(game.state, GameState.PLAYING)
                self.assertEqual(game.game_clock.ticks, 0)
                snapshots.append((game.enemy_x, game.enemy_y, game.player_x, game.player_y,
                                  game.lives, game.run_score, game.rng.getstate()))
            finally:
                game.cancel_death()
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])

    def test_music_stays_suspended_and_explosion_has_its_own_channel(self):
        game = self.game
        with mock.patch('pygame.mixer.music.pause') as pause, \
                mock.patch.object(game.music, 'update') as update:
            self.begin()
            pause.assert_called_once()
            self.advance_until(100)
            self.assertTrue(all(call.kwargs['paused'] for call in update.call_args_list))
            self.assertFalse(game.draw_channel.get_busy())
            self.assertNotEqual(game.draw_channel, game.death_channel)

    def test_missing_frame_loader_keeps_slots_and_one_scale_for_remaining_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = ROOT / folder / 'missing.png'
            source = ROOT / 'public' / MANIFEST['assets']['death_frames'][0]
            with contextlib.redirect_stdout(io.StringIO()):
                frames = load_animation_frames((missing, source, missing), (26, 30))
        self.assertEqual(len(frames), 3)
        self.assertIsNone(frames[0])
        self.assertIsNotNone(frames[1])
        self.assertIsNone(frames[2])


if __name__ == '__main__':
    unittest.main()
