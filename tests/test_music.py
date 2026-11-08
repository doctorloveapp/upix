"""Scoperta dinamica, shuffle completo, confine fra giri e stream singolo."""

import contextlib
import io
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import pygame

from music import MenuMusic, MusicShuffle, MusicPlayer


class MusicTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.directory = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def tracks(self, *names):
        for name in names: (self.directory / name).touch()

    def test_discovers_mp3_case_insensitively_without_configured_names(self):
        self.tracks('new.MP3', 'another.mp3', 'readme.txt')
        (self.directory / 'folder.mp3').mkdir()
        shuffle = MusicShuffle(self.directory)
        self.assertEqual([p.name for p in shuffle.tracks], ['another.mp3', 'new.MP3'])
        self.tracks('added.mp3')
        self.assertEqual(len(MusicShuffle(self.directory).tracks), 3)
        self.assertEqual(len(shuffle.tracks), 2)  # Snapshot all'avvio, niente I/O nel frame.

    def test_each_round_contains_every_track_once_and_boundaries_do_not_repeat(self):
        self.tracks('a.mp3', 'b.mp3', 'c.mp3', 'd.mp3')
        for seed in range(10):
            shuffle = MusicShuffle(self.directory, rng=random.Random(seed))
            stream = [shuffle.next_track() for _ in range(80)]
            for first in range(0, 80, 4):
                self.assertEqual(set(stream[first:first + 4]), set(shuffle.tracks))
            self.assertTrue(all(a != b for a, b in zip(stream, stream[1:])))

    def test_zero_one_and_two_tracks_never_hang(self):
        self.assertIsNone(MusicShuffle(self.directory).next_track())
        self.tracks('one.mp3')
        shuffle = MusicShuffle(self.directory)
        self.assertEqual([shuffle.next_track().name for _ in range(5)], ['one.mp3'] * 5)
        self.tracks('two.mp3')
        shuffle = MusicShuffle(self.directory, rng=random.Random(4))
        stream = [shuffle.next_track() for _ in range(20)]
        self.assertTrue(all(a != b for a, b in zip(stream, stream[1:])))

    def test_music_randomness_does_not_consume_global_simulation_randomness(self):
        self.tracks('a.mp3', 'b.mp3')
        state = random.getstate()
        shuffle = MusicShuffle(self.directory)
        for _ in range(10): shuffle.next_track()
        self.assertEqual(random.getstate(), state)

    def test_player_does_not_restart_on_level_change_and_advances_on_natural_end(self):
        self.tracks('a.mp3', 'b.mp3')
        player = MusicPlayer(self.directory, volume=.26, rng=random.Random(4))
        with mock.patch('pygame.mixer.get_init', return_value=(44100, -16, 2)), \
                mock.patch('pygame.mixer.music.load') as load, \
                mock.patch('pygame.mixer.music.play') as play, \
                mock.patch('pygame.mixer.music.set_volume'), \
                mock.patch('pygame.mixer.music.get_busy', return_value=False), \
                mock.patch('pygame.mixer.music.stop'):
            player.ensure_playing()
            first = player.current
            player.ensure_playing()  # Nuovo livello: stesso stream, nessuna ripartenza.
            player.update(paused=True)
            self.assertEqual(load.call_count, 1)
            play.assert_called_once_with()  # loops=0, niente loop infinito del singolo MP3.
            player.update()
            self.assertNotEqual(player.current, first)
            self.assertEqual(load.call_count, 2)
            player.stop()
            player.update()
            self.assertEqual(load.call_count, 2)

    def test_unplayable_catalog_stops_after_bounded_attempts(self):
        self.tracks('broken-a.mp3', 'broken-b.mp3')
        player = MusicPlayer(self.directory, volume=.26)
        with mock.patch('pygame.mixer.get_init', return_value=(44100, -16, 2)), \
                mock.patch('pygame.mixer.music.load', side_effect=pygame.error('invalid')) as load, \
                contextlib.redirect_stdout(io.StringIO()):
            player.ensure_playing()
            self.assertFalse(player.enabled)
            self.assertIsNone(player.current)
            self.assertEqual(load.call_count, 2)


class MenuMusicTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.enterContext(mock.patch('pygame.mixer.get_init', return_value=(44100, -16, 2)))
        self.load = self.enterContext(mock.patch('pygame.mixer.music.load'))
        self.play = self.enterContext(mock.patch('pygame.mixer.music.play'))
        self.volume = self.enterContext(mock.patch('pygame.mixer.music.set_volume'))
        self.stop = self.enterContext(mock.patch('pygame.mixer.music.stop'))
        self.blocking_fade = self.enterContext(mock.patch('pygame.mixer.music.fadeout'))
        self.player = MenuMusic('UPix.mp3', volume=.26, fade_in_ms=800, fade_out_ms=500,
                                time_source=lambda: self.now)

    def test_menu_loops_and_fades_in_without_restarting_between_screens(self):
        self.player.start()
        self.play.assert_called_once_with(loops=-1)
        self.volume.assert_called_with(0)
        self.now = 400
        self.player.update()
        self.volume.assert_called_with(.13)
        self.player.start()
        self.load.assert_called_once()
        self.now = 800
        self.player.update()
        self.volume.assert_called_with(.26)

    def test_fade_out_is_progressive_and_releases_stream_only_at_deadline(self):
        self.player.start()
        self.now = 800
        self.player.fade_out()
        self.assertTrue(self.player.active)
        self.now += 250
        self.player.update()
        self.volume.assert_called_with(.13)
        self.stop.assert_not_called()
        self.now += 249
        self.player.update()
        self.assertTrue(self.player.active)
        self.now += 1
        self.player.update()
        self.assertFalse(self.player.active)

        self.stop.assert_called_once()
        self.blocking_fade.assert_not_called()

    def test_start_during_fade_in_uses_current_gain_and_cancellation_restores_it(self):
        self.player.start()
        self.now = 400
        self.player.fade_out()
        self.volume.assert_called_with(.13)
        self.now += 250
        self.player.update()
        self.volume.assert_called_with(.065)
        self.player.start()  # Annulla la partenza, senza ricaricare il brano.
        self.load.assert_called_once()
        self.now += 800
        self.player.update()
        self.volume.assert_called_with(.26)
        self.assertTrue(self.player.active)

    def test_silent_immediate_start_and_zero_fades_never_delay_game(self):
        self.player.start()
        self.player.fade_out()  # Fade-in ancora a zero.
        self.assertFalse(self.player.active)
        instant = MenuMusic('UPix.mp3', volume=.26, fade_in_ms=0, fade_out_ms=0)
        instant.start()
        self.volume.assert_called_with(.26)
        instant.fade_out()
        self.assertFalse(instant.active)

    def test_missing_audio_and_missing_device_leave_game_available(self):
        self.load.side_effect = pygame.error('missing')
        with contextlib.redirect_stdout(io.StringIO()):
            self.player.start()
        self.assertFalse(self.player.active)
        self.player.fade_out()
        self.player.update()
        self.play.assert_not_called()
        with mock.patch('pygame.mixer.get_init', return_value=None):
            self.player.start()
        self.assertFalse(self.player.active)


class FirstLevelMusicTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.directory = Path(folder)
        for name in ('02gold.mp3', 'a.mp3', 'b.mp3'):
            (self.directory / name).touch()
        self.fixed = self.directory / '02gold.mp3'
        self.enterContext(mock.patch('pygame.mixer.get_init', return_value=(44100, -16, 2)))
        self.load = self.enterContext(mock.patch('pygame.mixer.music.load'))
        self.play = self.enterContext(mock.patch('pygame.mixer.music.play'))
        self.enterContext(mock.patch('pygame.mixer.music.set_volume'))
        self.enterContext(mock.patch('pygame.mixer.music.stop'))
        self.enterContext(mock.patch('pygame.mixer.music.get_busy', return_value=False))
        self.player = MusicPlayer(self.directory, volume=.26, rng=random.Random(1989))

    def test_level_one_always_plays_fixed_track_in_loop_and_pause_does_not_restart(self):
        self.player.play_level(1, self.fixed)
        self.assertEqual(self.player.current, self.fixed)
        self.play.assert_called_once_with(loops=-1)
        self.player.play_level(1, self.fixed)
        self.player.update(paused=True)
        self.load.assert_called_once()
        self.player.update()  # Ripristina soltanto il tema fisso se lo stream si interrompe.
        self.assertEqual(self.player.current, self.fixed)

    def test_level_two_switches_to_shuffle_and_subsequent_levels_keep_current_track(self):
        self.player.play_level(1, self.fixed)
        self.player.play_level(2, self.fixed)
        self.assertNotEqual(self.player.current, self.fixed)
        self.play.assert_called_with()
        self.load.reset_mock()
        current = self.player.current
        self.player.play_level(3, self.fixed)
        self.assertEqual(self.player.current, current)
        self.load.assert_not_called()
        self.player.stop()
        self.player.play_level(1, self.fixed)
        self.assertEqual(self.player.current, self.fixed)
        self.play.assert_called_with(loops=-1)

    def test_fixed_theme_counts_in_shuffle_round_without_repeating_before_other_tracks(self):
        for seed in range(10):
            shuffle = MusicShuffle(self.directory, rng=random.Random(seed))
            shuffle.mark_played(self.fixed)
            rest = [shuffle.next_track() for _ in range(2)]
            self.assertEqual(set(rest), set(shuffle.tracks) - {self.fixed})
            self.assertNotEqual(shuffle.next_track(), rest[-1])

    def test_missing_fixed_track_falls_back_to_shuffle_and_debug_starts_directly_in_shuffle(self):
        def load(path):
            if Path(path) == self.fixed:
                raise pygame.error('missing')
        self.load.side_effect = load
        with contextlib.redirect_stdout(io.StringIO()):
            self.player.play_level(1, self.fixed)
        self.assertIn(self.player.current, self.player.shuffle.tracks)
        self.assertNotEqual(self.player.current, self.fixed)
        self.player.stop()
        self.player.play_level(5, self.fixed)
        self.assertNotEqual(self.player.current, self.fixed)
