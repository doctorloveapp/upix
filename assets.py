"""Sfondi rasterizzati al cambio livello, senza lavoro SVG nel frame loop."""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pygame
from manifest import MANIFEST


def load_sprite(path: Path, max_size, scale=1.0):
    """Dimensioni fisiche/grafiche condivise; proporzioni e alpha preservati."""
    fallback = tuple(max(1, round(value * scale)) for value in max_size)
    try:
        source = pygame.image.load(str(path)).convert_alpha()
        factor = min(max_size[0] / source.get_width(), max_size[1] / source.get_height())
        base = (max(1, round(source.get_width() * factor)),
                max(1, round(source.get_height() * factor)))
        size = tuple(max(1, round(value * scale)) for value in base)
        return pygame.transform.scale(source, size), size
    except (pygame.error, OSError) as exc:
        print(f'Sprite non disponibile ({path}): {exc}')
        return None, fallback


def load_animation_frames(paths, reference_size, scale=1.0):
    """Un'unica scala per l'intera sequenza, ancorata al primo frame valido.

    Non normalizzare ogni fotogramma nel box: si perderebbe l'espansione
    originale dell'esplosione. I frame mancanti mantengono la propria durata.
    """
    sources = []
    for path in paths:
        try:
            sources.append(pygame.image.load(str(path)).convert_alpha())
        except (pygame.error, OSError) as exc:
            print(f'Fotogramma non disponibile ({path}): {exc}')
            sources.append(None)
    reference = next((source for source in sources if source is not None), None)
    if reference is None:
        return tuple(sources)
    factor = min(reference_size[0] / reference.get_width(),
                 reference_size[1] / reference.get_height()) * scale
    return tuple(None if source is None else pygame.transform.scale(source, (
        max(1, round(source.get_width() * factor)),
        max(1, round(source.get_height() * factor)))) for source in sources)


@lru_cache(maxsize=4)
def _svg_png(path: str, modified_ns: int, font_path: str) -> bytes:
    # Import locale: un errore SVG non impedisce il caricamento dell'immagine primaria.
    import resvg_py

    return resvg_py.svg_to_bytes(
        # Dimensioni intrinseche: un viewport intermedio quadrato introdurrebbe
        # bande prima del ritaglio, facendo perdere il rapporto originale.
        svg_path=path, background="#000000",
        skip_system_fonts=True, font_files=[font_path],
        font_family="FreeSans", monospace_family="FreeSans",
    )


def _cover_image(image: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    """Riempie il quadro con scala uniforme e ritaglio centrato (cover)."""
    scale = max(size[0] / image.get_width(), size[1] / image.get_height())
    target = (max(size[0], round(image.get_width() * scale)),
              max(size[1], round(image.get_height() * scale)))
    if image.get_size() != target:
        image = pygame.transform.smoothscale(image, target)
    background = pygame.Surface(size).convert()
    background.fill((0, 0, 0))
    background.blit(image, image.get_rect(center=(size[0] // 2, size[1] // 2)))
    return background


def _load_level_asset(asset_dir: Path, level: int, size: tuple[int, int],
                       suffixes: tuple[str, ...], stem: str
                       ) -> tuple[pygame.Surface | None, Path | None]:
    """Carica soltanto i formati del ruolo richiesto, senza scambiare i livelli."""
    for suffix in suffixes:
        path = asset_dir / (stem + suffix)
        if not path.is_file():
            continue
        try:
            if suffix == ".svg":
                font_path = str(Path(pygame.__file__).parent / pygame.font.get_default_font())
                png = _svg_png(str(path.resolve()), path.stat().st_mtime_ns, font_path)
                image = pygame.image.load(BytesIO(png), "background.png").convert_alpha()
            else:
                image = pygame.image.load(str(path)).convert_alpha()
            return _cover_image(image, size), path
        except (ImportError, pygame.error, OSError, ValueError) as exc:
            print(f"Risorsa livello non disponibile ({path}): {exc}")
    return None, None


def load_level_cover(asset_dir: Path, level: int,
                      size: tuple[int, int], *, source=None) -> tuple[pygame.Surface | None, Path | None]:
    """Copertura SVG visibile subito nelle aree non conquistate.

    Cache limitata e invalidata dal timestamp. Un errore non deve mostrare
    prematuramente l'immagine primaria: il chiamante usa una copertura neutra.
    """
    source = source if source is not None else MANIFEST['levels'][level - 1]['cover']
    return _load_level_asset(asset_dir, level, size, ('.svg',), str(Path(source).with_suffix('')))


def load_level_image(asset_dir: Path, level: int,
                      size: tuple[int, int], *, source=None) -> tuple[pygame.Surface | None, Path | None]:
    """PNG/JPG da rivelare: scala uniforme e ritaglio centrato, senza deformazioni.

    Nessuna sostituzione con l'SVG o banda nera introdotta dal letterboxing.
    """
    source = source if source is not None else MANIFEST['levels'][level - 1]['primary']
    return _load_level_asset(asset_dir, level, size, MANIFEST['assets']['primary_suffixes'], source)
