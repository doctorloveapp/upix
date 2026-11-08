"""Cache, invalidazione e normalizzazione: niente FFmpeg nel player o nei test unitari."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from audio_normalization import MusicNormalizer, NormalizationError


class NormalizationTests(unittest.TestCase):
    def test_encoded_loudness_feedback_corrects_gain_before_publishing_cache(self):
        outputs = iter((-12, -10.2))
        def measure(executable, source, target, peak):
            if Path(source).suffix == '.ogg':
                return dict(input_i=next(outputs), input_tp=-1, input_lra=5,
                            input_thresh=-30, target_offset=0)
            return self.measure(executable, source, target, peak)
        with mock.patch.object(self.normalizer, '_measure', side_effect=measure), \
                mock.patch.object(self.normalizer, '_render', side_effect=self.render) as render, \
                contextlib.redirect_stdout(io.StringIO()):
            self.normalizer.prepare([self.source], executable='ffmpeg-test')
        self.assertEqual(render.call_count, 2)
        self.assertEqual(render.call_args.args[-1], 2)
        self.assertNotEqual(self.normalizer.resolve(self.source), self.source)

    def setUp(self):
        self.folder = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.folder)
        (self.root / 'music').mkdir()
        self.reference = self.root / 'music/02gold.mp3'
        self.source = self.root / 'music/quiet.mp3'
        self.reference.write_bytes(b'reference')
        self.source.write_bytes(b'quiet')
        self.config = dict(enabled=True, reference='music/02gold.mp3', cache_dir='normalized',
                           true_peak_db=-2, loudness_range_lu=11, max_boost_db=18,
                           vorbis_quality=6, timeout_seconds=30)
        self.normalizer = MusicNormalizer(self.root, self.config)

    @staticmethod
    def measure(*args):
        source = Path(args[1])
        loudness = -10 if source.name == '02gold.mp3' or source.suffix == '.ogg' else -24
        return dict(input_i=loudness, input_tp=-2, input_lra=5, input_thresh=-34, target_offset=0)

    @staticmethod
    def render(executable, source, destination, *args):
        destination.write_bytes(b'normalized ogg test')

    def prepare(self):
        with mock.patch.object(self.normalizer, '_measure', side_effect=self.measure), \
                mock.patch.object(self.normalizer, '_render', side_effect=self.render) as render, \
                contextlib.redirect_stdout(io.StringIO()):
            self.normalizer.prepare([self.source], executable='ffmpeg-test')
        return render

    def test_quiet_track_uses_reference_and_cache_is_reused_without_transcoding(self):
        render = self.prepare()
        self.assertEqual(render.call_args.args[4], -10)
        resolved = self.normalizer.resolve(self.source)
        self.assertEqual(resolved.suffix, '.ogg')
        self.assertTrue(resolved.is_file())
        with mock.patch.object(self.normalizer, '_run', side_effect=AssertionError('DSP nel player')):
            self.assertEqual(self.normalizer.resolve(self.source), resolved)
            self.normalizer.prepare([self.source], executable='not-needed')
        index = json.loads(self.normalizer.index_path.read_text(encoding='utf-8'))
        self.assertEqual(index['tracks']['music/quiet.mp3']['gain_db'], 14)

    def test_source_reference_and_settings_changes_invalidate_cached_audio(self):
        self.prepare()
        self.source.write_bytes(b'updated quiet track')
        self.assertEqual(self.normalizer.resolve(self.source), self.source)
        self.prepare()
        self.reference.write_bytes(b'updated reference')
        self.assertEqual(self.normalizer.resolve(self.source), self.source)
        self.prepare()
        changed = MusicNormalizer(self.root, dict(self.config, true_peak_db=-3))
        self.assertEqual(changed.resolve(self.source), self.source)

    def test_corrupt_output_or_index_never_breaks_original_playback(self):
        self.prepare()
        output = self.normalizer.resolve(self.source)
        output.write_bytes(b'corrupt')
        self.assertEqual(self.normalizer.resolve(self.source), self.source)
        self.normalizer.index_path.write_text('{broken', encoding='utf-8')
        self.assertEqual(self.normalizer.resolve(self.source), self.source)

    def test_invalid_cache_path_is_rejected_and_failed_prepare_is_not_published(self):
        self.prepare()
        index = json.loads(self.normalizer.index_path.read_text(encoding='utf-8'))
        index['tracks']['music/quiet.mp3']['output'] = '../outside.ogg'
        self.normalizer.index_path.write_text(json.dumps(index), encoding='utf-8')
        self.assertEqual(self.normalizer.resolve(self.source), self.source)
        with mock.patch.object(self.normalizer, '_measure', side_effect=self.measure), \
                mock.patch.object(self.normalizer, '_render', side_effect=NormalizationError('failure')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.normalizer.prepare([self.source], executable='ffmpeg-test')
        self.assertEqual(self.normalizer.resolve(self.source), self.source)

    def test_silent_measurements_are_rejected(self):
        stats = dict(input_i='-inf', input_tp='-inf', input_lra='0', input_thresh='-70', target_offset='inf')
        with self.assertRaises(NormalizationError):
            self.normalizer._stats('diagnostic\n' + json.dumps(stats))

    def test_boost_cap_is_applied_before_rendering(self):
        self.normalizer.config['max_boost_db'] = 8
        def measure(executable, source, target, peak):
            if Path(source).suffix == '.ogg':
                return dict(input_i=target, input_tp=-2, input_lra=5, input_thresh=-30, target_offset=0)
            return self.measure(executable, source, target, peak)
        with mock.patch.object(self.normalizer, '_measure', side_effect=measure), \
                mock.patch.object(self.normalizer, '_render', side_effect=self.render) as render, \
                contextlib.redirect_stdout(io.StringIO()):
            self.normalizer.prepare([self.source], executable='ffmpeg-test')
        self.assertEqual(render.call_args.args[4], -16)
