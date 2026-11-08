"""HUD composto in coordinate di finestra, fuori dalla superficie di gioco."""

from dataclasses import dataclass
from pathlib import Path
import pygame
from manifest import MANIFEST, ROOT
from localization import I18N, tr

FRAME_PATH = ROOT / MANIFEST['assets']['root'] / MANIFEST['assets']['frame']
FRAME_DESIGN_SIZE = MANIFEST['frame']['design_size']
# Rettangoli misurati sul file originale: estremi esclusivi, senza decorazioni.
FRAME_GAME_AREA = MANIFEST['frame']['game_area']
FRAME_VALUES = MANIFEST['frame']['values']
FRAME_FOOTER = MANIFEST['frame']['footer']


@dataclass(frozen=True, slots=True)
class HudData:
    level: int
    lives: int
    percent: float
    target: float
    score: int
    seconds: int
    hint: str
    bonus: int = 0
    shields: int = 0
    cycle: int = 1


class Hud:
    """Cornice originale e valori nei pannelli; cache RGBA composta una sola volta."""

    def __init__(self, width: int, height: int = 768, *, frame_path: Path = FRAME_PATH):
        scale = min(width / FRAME_DESIGN_SIZE[0], height / FRAME_DESIGN_SIZE[1])
        size = tuple(round(value * scale) for value in FRAME_DESIGN_SIZE)
        self.frame_bounds = pygame.Rect((0, 0), size)
        self.frame_bounds.center = (width // 2, height // 2)

        def project(bounds):
            x, y, w, h = bounds
            left = self.frame_bounds.left + round(x * scale)
            top = self.frame_bounds.top + round(y * scale)
            right = self.frame_bounds.left + round((x + w) * scale)
            bottom = self.frame_bounds.top + round((y + h) * scale)
            return pygame.Rect(left, top, right - left, bottom - top)

        self.game_area = project(FRAME_GAME_AREA)
        self.value_bounds = {key: project(bounds) for key, bounds in FRAME_VALUES.items()}
        self.footer_bounds = project(FRAME_FOOTER)
        self._frame = pygame.Surface((width, height), pygame.SRCALPHA).convert_alpha()
        try:
            source = pygame.image.load(str(frame_path)).convert_alpha()
            self._frame.blit(pygame.transform.scale(source, size), self.frame_bounds)
        except (pygame.error, OSError) as exc:
            print(f'Cornice non disponibile ({frame_path}): {exc}')
            # Fallback funzionale con la stessa geometria, senza coprire il campo.
            for bounds in self.value_bounds.values():
                panel = bounds.move(-90, 0).inflate(100, 10)
                pygame.draw.rect(self._frame, (20, 23, 30), panel)
        self._base_frame = self._frame.copy()
        self._label_bounds = {key: project(rect) for key, rect in MANIFEST['frame']['labels'].items()}
        self._label_font = pygame.font.SysFont(MANIFEST['assets']['font'], max(10, round(30 * scale)), bold=True)
        self._refresh_labels()
        self._surface = self._frame.copy()
        style = MANIFEST['ui']
        self._font = pygame.font.SysFont(MANIFEST['assets']['font'],
            max(style['hud_value_min_size'], round(style['hud_value_font_size'] * scale)), bold=True)
        self._footer_font = pygame.font.SysFont(MANIFEST['assets']['font'],
            max(style['hud_footer_min_size'], round(style['hud_footer_font_size'] * scale)), bold=True)
        self._last_data = None

    def _refresh_labels(self):
        # Il PNG contiene label italiane: maschera soltanto i rettangoli del
        # testo, preservando logo, pannelli, valori e apertura del campo.
        self._frame = self._base_frame.copy()
        for key, rect in self._label_bounds.items():
            pygame.draw.rect(self._frame, (10, 12, 18), rect)
            label = self._label_font.render(tr({'level': 'header_level', 'percent': 'header_capture',
                                         'lives': 'header_lives'}[key]), True, MANIFEST['colors']['text'])
            if label.get_width() > rect.width:
                ratio = rect.width / label.get_width()
                label = pygame.transform.smoothscale(label, (rect.width, max(1, round(label.get_height() * ratio))))
            self._frame.blit(label, label.get_rect(center=rect.center))
        self._language = I18N.language

    def draw(self, window: pygame.Surface, data: HudData) -> None:
        if self._language != I18N.language:
            self._refresh_labels()
            self._last_data = None
        if data != self._last_data:
            self._surface.fill((0, 0, 0, 0))
            self._surface.blit(self._frame, (0, 0))
            values = {'level': f'{data.level:02d}' if data.level else '--',
                      'percent': f'{data.percent:.1f}%' if data.level else '--',
                      'lives': tr('hud_lives_shields', lives=data.lives, shields=data.shields) if data.level else '--'}
            for key, value in values.items():
                bounds = self.value_bounds[key]
                text = self._font.render(value, True, MANIFEST['colors']['accent'])
                if text.get_width() > bounds.width:
                    text = pygame.transform.smoothscale(
                        text, (bounds.width, round(text.get_height() * bounds.width / text.get_width())))
                self._surface.blit(text, text.get_rect(center=bounds.center))
            label = tr('hud_footer', score=data.score, shields=data.shields, cycle=data.cycle,
                       bonus=data.bonus, minutes=data.seconds // 60, seconds=data.seconds % 60)
            pygame.draw.rect(self._surface, (10, 12, 18), self.footer_bounds)
            text = self._footer_font.render(label, True, (245, 245, 250))
            ratio = min(1, self.footer_bounds.width / text.get_width(),
                        self.footer_bounds.height / text.get_height())
            if ratio < 1:
                text = pygame.transform.smoothscale(
                    text, (max(1, round(text.get_width() * ratio)),
                           max(1, round(text.get_height() * ratio))))
            self._surface.blit(text, text.get_rect(center=self.footer_bounds.center))
            self._last_data = data
        window.blit(self._surface, (0, 0))
