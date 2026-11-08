"""Cataloghi completi, fallback e parametri di formattazione coerenti."""

import os
import unittest
from unittest import mock

from localization import I18N, Localizer, system_language
from manifest import ROOT, MANIFEST


class LocalizationTests(unittest.TestCase):
    def test_italian_english_and_unsupported_language(self):
        directory = ROOT / MANIFEST['i18n']['directory']
        italian = Localizer(directory, 'it-IT')
        english = Localizer(directory, 'en_US')
        self.assertEqual(italian['menu_items'][2], 'Come si gioca')
        self.assertEqual(english['menu_items'][2], 'How to Play')
        self.assertEqual(Localizer(directory, 'fr_FR').language, 'en')
        self.assertIn('76', italian.text('summary_extra_life', lives=1, threshold=76))

    def test_all_labels_and_level_hints_exist_in_both_catalogs(self):
        for config in MANIFEST['levels']:
            self.assertIn(config['hint'], I18N.catalogs['it'])
            self.assertIn(config['hint'], I18N.catalogs['en'])
        self.assertEqual(len(I18N['menu_items']), len(MANIFEST['ui']['menu_actions']))
        self.assertNotIn('strings', MANIFEST['ui'])

    def test_explicit_environment_override_has_priority(self):
        with mock.patch.dict(os.environ, {'UPIX_LANGUAGE': 'it_IT', 'LANG': 'en_US'}):
            self.assertEqual(system_language(), 'it_IT')
