"""Preparazione incrementale della musica e lettura della cache senza DSP nel gioco.

Gli originali non vengono modificati. FFmpeg è richiesto soltanto per creare
gli OGG normalizzati; il player usa la cache già pronta anche senza FFmpeg.
"""

from functools import lru_cache
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


class NormalizationError(ValueError):
    pass


@lru_cache(maxsize=128)
def _digest_cached(path, size, modified_ns):
    with open(path, 'rb') as stream:
        return sha256(stream.read()).hexdigest()


def file_digest(path):
    path = Path(path).resolve()
    stat = path.stat()
    return _digest_cached(str(path), stat.st_size, stat.st_mtime_ns)


class MusicNormalizer:
    VERSION = 2

    def __init__(self, asset_root, config, *, sample_rate=44100):
        self.root = Path(asset_root).resolve()
        self.config = dict(config)
        self.sample_rate = sample_rate
        self.reference = self.root / config['reference']
        self.cache = self.root / config['cache_dir']
        self.index_path = self.cache / 'index.json'

    def _settings_hash(self):
        settings = {key: self.config[key] for key in (
            'reference', 'true_peak_db', 'loudness_range_lu', 'max_boost_db', 'vorbis_quality')}
        settings.update(version=self.VERSION, sample_rate=self.sample_rate,
                        reference_hash=file_digest(self.reference))
        return sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()

    def _read_index(self):
        try:
            index = json.loads(self.index_path.read_text(encoding='utf-8'))
            if index['version'] == self.VERSION and index['settings_hash'] == self._settings_hash():
                if (isinstance(index['tracks'], dict)
                        and type(index['reference_lufs']) in (int, float)
                        and math.isfinite(index['reference_lufs'])):
                    return index
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def _cached_path(self, path, index):
        try:
            key = path.resolve().relative_to(self.root).as_posix()
            entry = index['tracks'][key]
            filename = entry['output']
            if (Path(filename).name != filename or '/' in filename or '\\' in filename
                    or Path(filename).suffix != '.ogg'):
                return None
            output = self.cache / filename
            if (entry['source_hash'] == file_digest(path) and output.is_file()
                    and entry['output_hash'] == file_digest(output)):
                return output
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def resolve(self, source):
        source = Path(source)
        if not self.config['enabled'] or not source.resolve().is_relative_to(self.root):
            return source
        index = self._read_index()
        return self._cached_path(source, index) or source if index else source

    def _run(self, executable, args):
        try:
            result = subprocess.run(
                [str(executable), '-hide_banner', '-nostdin', '-nostats', *args],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=self.config['timeout_seconds'], check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NormalizationError(str(exc)) from exc
        if result.returncode:
            raise NormalizationError(result.stderr[-1500:])
        return result.stderr

    @staticmethod
    def _stats(text):
        try:
            stats = json.loads(text[text.rindex('{'):text.rindex('}') + 1])
            for key in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset'):
                stats[key] = float(stats[key])
                if not math.isfinite(stats[key]):
                    raise ValueError('Audio silenzioso o misura non finita')
            return stats
        except (ValueError, KeyError, TypeError) as exc:
            raise NormalizationError('Misura loudness non valida') from exc

    def _measure(self, executable, source, target, peak):
        filter_text = (f"loudnorm=I={target}:TP={peak}:LRA={self.config['loudness_range_lu']}:"
                       'print_format=json')
        return self._stats(self._run(executable, [
            '-i', str(source), '-vn', '-filter_threads', '1', '-af', filter_text,
            '-f', 'null', os.devnull]))

    def _render(self, executable, source, destination, stats, target, peak, correction_db=0):
        filter_text = (
            f"loudnorm=I={target}:TP={peak}:LRA={self.config['loudness_range_lu']}:"
            f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
            f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
            f"offset={stats['target_offset']}:linear=true,volume={correction_db}dB,"
            f"alimiter=limit={10 ** (peak / 20):.8f}:level=false:latency=true")
        self._run(executable, [
            '-y', '-i', str(source), '-vn', '-map_metadata', '-1', '-filter_threads', '1',
            '-af', filter_text, '-ar', str(self.sample_rate), '-ac', '2',
            '-c:a', 'libvorbis', '-q:a', str(self.config['vorbis_quality']), str(destination)])

    def _write_index(self, index):
        temporary = self.index_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.index_path)

    def prepare(self, sources, *, executable=None):
        """Preparazione fuori dal loop; una misura/render/verifica per i soli file cambiati."""
        if not self.config['enabled']:
            return {}
        try:
            index = self._read_index()
            settings_hash = self._settings_hash()
        except OSError as exc:
            print(f'Normalizzazione musica non disponibile: {exc}')
            return {}
        sources = tuple(dict.fromkeys(Path(path).resolve() for path in sources))
        stale = [source for source in sources if not index or not self._cached_path(source, index)]
        if not stale:
            return index['tracks']
        executable = executable or shutil.which('ffmpeg')
        if not executable:
            print('FFmpeg assente: riproduzione degli originali per i brani senza cache aggiornata.')
            return index['tracks'] if index else {}
        self.cache.mkdir(parents=True, exist_ok=True)
        if index is None:
            reference = self._measure(executable, self.reference, -16, self.config['true_peak_db'])
            index = dict(version=self.VERSION, settings_hash=settings_hash,
                         reference_lufs=reference['input_i'], tracks={})
        reference_i = max(-70, min(-5, index['reference_lufs']))
        for source in stale:
            temporary = None
            try:
                key = source.relative_to(self.root).as_posix()
                source_hash = file_digest(source)
                filename = sha256((key + source_hash + settings_hash).encode()).hexdigest()[:32] + '.ogg'
                destination = self.cache / filename
                temporary = destination.with_suffix('.tmp.ogg')
                peak = self.config['true_peak_db']
                stats = self._measure(executable, source, reference_i, peak)
                if stats['input_i'] + self.config['max_boost_db'] < -70:
                    raise NormalizationError('Segnale sotto il limite normalizzabile con il guadagno ammesso')
                target = max(-70, min(reference_i, stats['input_i'] + self.config['max_boost_db']))
                if target != reference_i:
                    stats = self._measure(executable, source, target, peak)
                # Verifica anche l'OGG decodificato: il codec può introdurre overshoot.
                correction = 0.0
                for attempt in range(4):
                    self._render(executable, source, temporary, stats, target, peak, correction)
                    measured = self._measure(executable, temporary, target, peak)
                    loudness_error = target - measured['input_i']
                    if measured['input_tp'] <= -0.1 and abs(loudness_error) <= .5:
                        break
                    if measured['input_tp'] > -.1:
                        peak = max(-9, peak - measured['input_tp'] - .5)
                        stats = self._measure(executable, source, target, peak)
                    correction = max(-6, min(6, correction + loudness_error))
                else:
                    raise NormalizationError('Loudness o picchi fuori tolleranza dopo la codifica OGG')
                temporary.replace(destination)
                index['tracks'][key] = dict(
                    output=filename, source_hash=source_hash, output_hash=file_digest(destination),
                    input_lufs=stats['input_i'], target_lufs=target, output_lufs=measured['input_i'],
                    output_true_peak_db=measured['input_tp'],
                    gain_db=round(measured['input_i'] - stats['input_i'], 2))
                self._write_index(index)
                print(f"Audio {source.name}: {stats['input_i']:.2f} -> {measured['input_i']:.2f} LUFS, "
                      f"picco {measured['input_tp']:.2f} dBTP")
            except (NormalizationError, OSError, ValueError) as exc:
                print(f'Normalizzazione saltata ({source.name}): {exc}')
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
        return index['tracks']


def configured_normalizer():
    from manifest import MANIFEST, ROOT
    return MusicNormalizer(ROOT / MANIFEST['assets']['root'], MANIFEST['audio']['normalization'],
                           sample_rate=MANIFEST['audio']['sample_rate'])


def normalized_music_path(source):
    return configured_normalizer().resolve(source)


def prepare_configured_audio():
    from manifest import MANIFEST, ROOT
    config = MANIFEST['audio']['normalization']
    # La release contiene già la cache: niente encoder o scritture nella cartella estratta.
    if not config['enabled'] or not config['prepare_on_startup'] or getattr(sys, 'frozen', False):
        return
    root = ROOT / MANIFEST['assets']['root']
    directory = root / MANIFEST['assets']['music_dir']
    try:
        sources = sorted(path for path in directory.iterdir()
                         if path.is_file() and path.suffix.lower() == '.mp3')
        sources.append(root / MANIFEST['assets']['menu_music'])
        configured_normalizer().prepare(sources)
    except (NormalizationError, OSError) as exc:
        print(f'Preparazione audio non disponibile: {exc}')


if __name__ == '__main__':
    prepare_configured_audio()
