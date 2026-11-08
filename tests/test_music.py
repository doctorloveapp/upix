"""Scoperta dinamica, shuffle completo, confine fra giri e stream singolo."""

import contextlib
import io
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import pygame

from music import MusicShuffle, MusicPlayer


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
