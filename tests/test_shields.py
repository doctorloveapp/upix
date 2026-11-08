"""Soglia inclusiva, equipaggiamento singolo, inventario e grazia temporale."""

import unittest

from manifest import MANIFEST
from shields import Shields


class ShieldTests(unittest.TestCase):
    def setUp(self):
        self.shields = Shields(MANIFEST['shields'], 60)

    def test_single_capture_threshold_is_inclusive_and_not_cumulative(self):
        self.assertFalse(self.shields.award(249, 1000))
        self.assertFalse(self.shields.award(249, 1000))
        self.assertEqual(self.shields.charges, 0)
        self.assertTrue(self.shields.award(250, 1000))
        self.assertEqual(self.shields.charges, 1)
        self.assertGreater(self.shields.notice_ticks, 0)

    def test_one_contact_consumes_one_charge_and_grace_prevents_duplicate_hit(self):
        self.assertFalse(self.shields.activate())
        self.shields.award(25, 100)
        self.shields.award(25, 100)
        self.assertTrue(self.shields.activate())
        self.assertFalse(self.shields.activate())
        self.assertTrue(self.shields.absorb())
        self.assertEqual(self.shields.charges, 1)
        self.assertFalse(self.shields.active)
        self.assertTrue(self.shields.absorb())
        for _ in range(30): self.shields.advance()
        self.assertFalse(self.shields.absorb())
        self.assertEqual(self.shields.charges, 1)

    def test_level_reset_stows_equipped_shield_but_preserves_inventory(self):
        self.shields.award(25, 100)
        self.shields.activate()
        self.shields.start_level()
        self.assertEqual(self.shields.charges, 1)
        self.assertFalse(self.shields.active)
        self.assertEqual(self.shields.earned_this_level, 0)
        self.assertEqual(self.shields.notice_ticks, 0)
