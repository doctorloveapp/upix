"""Proiezione del frame completo; nessuna coordinata fisica viene modificata."""

import pygame
from collections.abc import Callable


class Viewport:
    """Una superficie logica, scalata uniformemente al solo momento di presentare.

    Se i rapporti di aspetto differiscono, centra il campo con bande nere.
    Le coordinate di gioco restano sempre relative alla superficie logica.
    """

    def __init__(self, window: pygame.Surface, logical_size: tuple[int, int], *, area=None):
        self.window = window
        width, height = logical_size
        if width <= 0 or height <= 0:
            raise ValueError("Le dimensioni logiche devono essere positive")
        self.surface = pygame.Surface(logical_size).convert(window)
        area = window.get_rect() if area is None else pygame.Rect(area)
        if area.width <= 0 or area.height <= 0 or not window.get_rect().contains(area):
            raise ValueError("L'area del viewport deve essere interna alla finestra")
        self.scale = min(area.width / width, area.height / height)
        size = (round(width * self.scale), round(height * self.scale))
        self.bounds = pygame.Rect((0, 0), size)
        self.bounds.center = area.center
        self._scaled = pygame.Surface(size).convert(window)

    def logical_to_window(self, x: float, y: float) -> tuple[float, float]:
        return self.bounds.left + x * self.scale, self.bounds.top + y * self.scale

    def window_to_logical(self, x: float, y: float) -> tuple[float, float] | None:
        if not self.bounds.collidepoint(x, y):
            return None
        return (x - self.bounds.left) / self.scale, (y - self.bounds.top) / self.scale

    def present(self, overlay: Callable[[pygame.Surface], None] | None = None) -> None:
        # Nearest-neighbor per pixel art; buffer di destinazione riutilizzato.
        pygame.transform.scale(self.surface, self.bounds.size, self._scaled)
        self.window.fill((0, 0, 0))
        self.window.blit(self._scaled, self.bounds)
        if overlay is not None:
            overlay(self.window)
        pygame.display.flip()
