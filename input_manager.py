"""Azioni indipendenti dal dispositivo; hotplug joystick per instance ID."""

from dataclasses import dataclass
import pygame

from controls import KEYS
from manifest import MANIFEST


@dataclass(frozen=True, slots=True)
class InputFrame:
    direction: tuple[int, int] = (0, 0)


def keyboard_direction(keys):
    for action, vector in (('up', (0, -1)), ('down', (0, 1)),
                           ('left', (-1, 0)), ('right', (1, 0))):
        if keys[KEYS[action]]:
            return vector
    return 0, 0


class InputManager:
    def __init__(self, config=None, *, backend=None):
        self.config = config or MANIFEST['controller']
        self.backend = backend or pygame.joystick
        self.devices = {}
        self.axes = {}
        self.last_direction = {}
        self.focused = True
        self.disconnected = False
        self.backend.init()
        for index in range(self.backend.get_count()):
            self._open(index)

    def _open(self, index):
        try:
            device = self.backend.Joystick(index)
            self.devices[device.get_instance_id()] = device
        except pygame.error:
            pass

    def _cardinal(self, instance, x, y):
        previous = self.last_direction.get(instance, (0, 0))
        candidate = (1 if x > 0 else -1, 0) if abs(x) > abs(y) else (0, 1 if y > 0 else -1)
        threshold = (self.config['release_deadzone'] if candidate == previous
                     and previous != (0, 0) else self.config['deadzone'])
        if max(abs(x), abs(y)) <= threshold:
            result = (0, 0)
        else:
            result = candidate
        self.last_direction[instance] = result
        return result

    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self.last_direction.clear()
            return ()
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
        if event.type == pygame.JOYDEVICEADDED:
            self._open(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            device = self.devices.pop(event.instance_id, None)
            if device is not None:
                device.quit()
            self.axes.pop(event.instance_id, None)
            self.last_direction.pop(event.instance_id, None)
            self.disconnected = True
        if not self.focused:
            return ()
        if event.type == pygame.KEYDOWN:
            return tuple(action for action, key in KEYS.items() if key == event.key)
        instance = getattr(event, 'instance_id', None)
        if instance not in self.devices:
            return ()
        if event.type == pygame.JOYBUTTONDOWN:
            return tuple(action for action, button in self.config['buttons'].items() if button == event.button)
        previous = self.last_direction.get(instance, (0, 0))
        if event.type == pygame.JOYAXISMOTION:
            axes = self.axes.setdefault(instance, [0.0, 0.0])
            if event.axis in self.config['axes']:
                axes[self.config['axes'].index(event.axis)] = event.value
            direction = self._cardinal(instance, *axes)
        elif event.type == pygame.JOYHATMOTION:
            direction = self._cardinal(instance, event.value[0], -event.value[1])
        else:
            return ()
        if direction == previous or direction == (0, 0):
            return ()
        return ({(0, -1): 'up', (0, 1): 'down', (-1, 0): 'left', (1, 0): 'right'}[direction],)

    def sample(self, keys=None):
        if not self.focused:
            return InputFrame()
        direction = keyboard_direction(pygame.key.get_pressed() if keys is None else keys)
        if direction != (0, 0):
            return InputFrame(direction)
        for instance, device in sorted(self.devices.items()):
            try:
                x, y = (device.get_axis(axis) if axis < device.get_numaxes() else 0
                        for axis in self.config['axes'])
                if device.get_numhats():
                    hx, hy = device.get_hat(0)
                    if hx or hy:
                        x, y = hx, -hy
                direction = self._cardinal(instance, x, y)
                if direction != (0, 0):
                    return InputFrame(direction)
            except pygame.error:
                self.last_direction.pop(instance, None)
        return InputFrame()

    def close(self):
        for device in self.devices.values():
            device.quit()
        self.devices.clear()
