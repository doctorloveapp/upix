"""Build riproducibile Windows x64; nessuna operazione sul controllo versione."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def package_release():
    output = ROOT / 'dist/UPIX1989-Windows-x64.zip'
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for filename in ('UPIX1989.exe', 'game_manifest.json', 'LEGGIMI.txt', 'build_info.json'):
            archive.write(ROOT / 'dist' / filename, filename)
    return output


def main():
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise SystemExit('Questa build richiede Windows e Python a 64 bit.')
    from audio_normalization import prepare_configured_audio, configured_normalizer
    from manifest import MANIFEST
    prepare_configured_audio()
    normalizer = configured_normalizer()
    assets = ROOT / MANIFEST['assets']['root']
    sources = [*sorted((assets / MANIFEST['assets']['music_dir']).glob('*.mp3')),
               assets / MANIFEST['assets']['menu_music']]
    missing = [path.name for path in sources if normalizer.resolve(path) == path]
    if missing:
        raise SystemExit(f'Cache audio incompleta: {missing}. Preparare con FFmpeg prima della build.')
    index = json.loads(normalizer.index_path.read_text(encoding='utf-8'))
    cache_files = {'index.json', *(item['output'] for item in index['tracks'].values())}
    files = [path for path in assets.rglob('*') if path.is_file() and (
        not path.is_relative_to(normalizer.cache)
        or path.parent == normalizer.cache and path.name in cache_files)]
    identity = repr([(str(path.relative_to(assets)), path.stat().st_size, path.stat().st_mtime_ns)
                     for path in files])
    stage = ROOT / 'build' / ('assets-' + sha256(identity.encode()).hexdigest()[:12]) / 'public'
    assert stage.resolve().is_relative_to((ROOT / 'build').resolve())
    for path in files:
        destination = stage / path.relative_to(assets)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed',
        '--name', 'UPIX1989', '--icon', str(assets / MANIFEST['assets']['player_sprite']),
        '--distpath', str(ROOT / 'dist'), '--workpath', str(ROOT / 'build/pyinstaller'),
        '--specpath', str(ROOT / 'build'), '--paths', str(ROOT),
        '--add-data', f'{stage};public', '--add-data', f'{ROOT / "locales"};locales',
        '--add-data', f'{ROOT / "game_manifest.json"};.', '--collect-all', 'resvg_py',
        '--collect-data', 'pygame', str(ROOT / 'desktop_launcher.py')], cwd=ROOT, check=True)
    executable = ROOT / 'dist/UPIX1989.exe'
    shutil.copy2(ROOT / 'game_manifest.json', ROOT / 'dist/game_manifest.json')
    shutil.copy2(ROOT / 'RELEASE_WINDOWS.md', ROOT / 'dist/LEGGIMI.txt')
    metadata = dict(platform='Windows x64', python=sys.version.split()[0],
                    manifest_hash=MANIFEST['fingerprint'], bytes=executable.stat().st_size,
                    sha256=sha256(executable.read_bytes()).hexdigest())
    (ROOT / 'dist/build_info.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))
    print(package_release())


if __name__ == '__main__':
    main()
