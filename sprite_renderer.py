"""Sprite direzionale con cache limitata; nessuna modifica alla fisica."""

import math

import pygame

from assets import load_sprite


class DirectionalSprite:
    def __init__(self, path, max_size, config):
        self.image, self.size = load_sprite(path, max_size)
        self.rotate = config['rotate_with_velocity']
        self.source_angle = config['source_angle_degrees']
        self.step = config['rotation_step_degrees']
        self.color = config['fallback_color']
        # Numero massimo di orientamenti noto, anche con traiettorie arbitrarie.
        self._frames = {}

    def angle_for(self, velocity):
        if not self.rotate or velocity == (0, 0):
            return 0
        # Coordinate schermo: y verso il basso; pygame.rotate usa angoli antiorari.
        angle = -math.degrees(math.atan2(velocity[1], velocity[0])) + self.source_angle
        return (round(angle / self.step) * self.step) % 360

    def frame_for(self, velocity):
        if self.image is None:
            return None
        angle = self.angle_for(velocity)
        if angle not in self._frames:
            self._frames[angle] = pygame.transform.rotate(self.image, angle)
        return self._frames[angle]

    def draw(self, surface, position, velocity):
        frame = self.frame_for(velocity)
        center = tuple(round(value) for value in position)
        if frame is not None:
            surface.blit(frame, frame.get_rect(center=center))
        else:
            rect = pygame.Rect((0, 0), self.size)
            rect.center = center
            pygame.draw.ellipse(surface, self.color, rect)
