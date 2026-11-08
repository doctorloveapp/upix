"""Sequenza nascosta con prefissi sovrapposti e impostazioni limitate."""

import unittest

from debug_menu import CheatSequence, StartSettings
from manifest import MANIFEST


class DebugMenuTests(unittest.TestCase):
    def setUp(self):
        self.sequence = MANIFEST['debug_menu']['sequence']
        self.cheat = CheatSequence(self.sequence)

    def test_only_the_complete_exact_sequence_activates(self):
        for action in self.sequence[:-1]:
            self.assertFalse(self.cheat.feed(action))
        self.assertTrue(self.cheat.feed(self.sequence[-1]))
        self.assertFalse(self.cheat.feed('shield'))

    def test_mismatch_recovery_overlapping_prefix_and_explicit_reset(self):
        for action in ('up', 'down', 'right', 'up', 'shield'):
            self.assertFalse(self.cheat.feed(action))
        self.cheat.feed('up')
        detected = [self.cheat.feed(action) for action in self.sequence]
        self.assertEqual(detected, [False] * 6 + [True])
        self.cheat.feed('up')
        self.cheat.reset()
        for action in self.sequence[1:]:
            self.assertFalse(self.cheat.feed(action))

    def test_bounds_and_defaults_do_not_modify_the_manifest(self):
        settings = StartSettings()
        self.assertEqual((settings.level, settings.lives, settings.shields), (1, 5, 0))
        self.assertEqual(settings.adjust('level', 999).level, 12)
        self.assertEqual(settings.adjust('level', -999).level, 1)
        self.assertEqual(settings.adjust('shields', -1).shields, 0)
        self.assertEqual(settings.lives, 5)
        for args in ({'level': 13}, {'lives': 0}, {'shields': -1}, {'lives': True}):
            with self.assertRaises(ValueError): StartSettings(**args)
