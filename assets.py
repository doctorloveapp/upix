"""Sfondi rasterizzati al cambio livello, senza lavoro SVG nel frame loop."""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pygame


@lru_cache(maxsize=4)
def _svg_png(path: str, modified_ns: int, size: tuple[int, int], font_path: str) -> bytes:
    # Import locale: senza renderer resta disponibile il fallback raster.
    import resvg_py

    return resvg_py.svg_to_bytes(
        svg_path=path, width=size[0], height=size[1], background="#000000",
        skip_system_fonts=True, font_files=[font_path],
        font_family="FreeSans", monospace_family="FreeSans",
    )


def load_level_background(asset_dir: Path, level: int,
                          size: tuple[int, int]) -> tuple[pygame.Surface | None, Path | None]:
    """SVG prioritario, poi PNG/JPG; proporzioni preservate su base nera.

    La cache SVG è limitata e invalidata dal timestamp del file. Restituisce
    anche la sorgente effettiva per diagnostica e verifiche del reveal.
    """
    for suffix in (".svg", ".png", ".jpg"):
        path = asset_dir / "assets" / f"{level:02d}{suffix}"
        if not path.is_file():
            continue
        try:
            if suffix == ".svg":
                font_path = str(Path(pygame.__file__).parent / pygame.font.get_default_font())
                png = _svg_png(str(path.resolve()), path.stat().st_mtime_ns, size, font_path)
                image = pygame.image.load(BytesIO(png), "background.png").convert_alpha()
            else:
                image = pygame.image.load(str(path)).convert_alpha()
            scale = min(size[0] / image.get_width(), size[1] / image.get_height())
            target = (max(1, round(image.get_width() * scale)),
                      max(1, round(image.get_height() * scale)))
            if image.get_size() != target:
                image = pygame.transform.smoothscale(image, target)
            background = pygame.Surface(size).convert()
            background.fill((0, 0, 0))
            background.blit(image, image.get_rect(center=(size[0] // 2, size[1] // 2)))
            return background, path
        except (ImportError, pygame.error, OSError, ValueError) as exc:
            print(f"Sfondo non disponibile ({path}): {exc}")
    return None, None
