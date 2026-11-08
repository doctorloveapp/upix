"""Tastiera/controller: deadzone, hotplug, direzioni cardinali e azioni."""

from types import SimpleNamespace
from collections import defaultdict
import unittest
from unittest import mock

import pygame

from input_manager import InputManager
from controls import KEYS


class Pad:
    def __init__(self, instance):
        self.instance = instance
        self.axes = [0.0, 0.0]
        self.hat = (0, 0)
        self.closed = False

    def get_instance_id(self): return self.instance
    def get_numaxes(self): return 2
    def get_axis(self, index): return self.axes[index]
    def get_numhats(self): return 1
    def get_hat(self, index): return self.hat
    def quit(self): self.closed = True


class InputTests(unittest.TestCase):
    def setUp(self):
        self.pad = Pad(42)
        self.backend = SimpleNamespace(init=mock.Mock(), get_count=lambda: 1,
                                       Joystick=lambda index: self.pad)
        self.manager = InputManager(backend=self.backend)
        self.keys = defaultdict(bool)

    def event(self, kind, **fields):
        return self.manager.handle_event(pygame.event.Event(kind, **fields))

    def test_deadzone_hysteresis_and_cardinal_dominant_axis(self):
        self.pad.axes = [.24, -.1]
        self.assertEqual(self.manager.sample(self.keys).direction, (0, 0))
        self.pad.axes = [.8, -.6]
        self.assertEqual(self.manager.sample(self.keys).direction, (1, 0))
        self.pad.axes = [.2, .1]
        self.assertEqual(self.manager.sample(self.keys).direction, (1, 0))
        self.pad.axes = [.18, .18]
        self.assertEqual(self.manager.sample(self.keys).direction, (0, 0))
        self.pad.axes = [.1, -.9]
        self.assertEqual(self.manager.sample(self.keys).direction, (0, -1))
        self.pad.axes = [.2, 0]
        self.assertEqual(self.manager.sample(self.keys).direction, (0, 0))  # cambio asse richiede 0,25

    def test_hat_keyboard_priority_and_held_movement(self):
        self.pad.hat = (0, 1)
        self.assertEqual(self.manager.sample(self.keys).direction, (0, -1))
        self.keys[KEYS['left']] = True
        self.assertEqual(self.manager.sample(self.keys).direction, (-1, 0))
        self.assertEqual(self.manager.sample(self.keys).direction, (-1, 0))

    def test_menu_axis_edge_and_buttons_map_to_actions(self):
        self.assertEqual(self.event(pygame.JOYAXISMOTION, instance_id=42, axis=1, value=.8), ('down',))
        self.assertEqual(self.event(pygame.JOYAXISMOTION, instance_id=42, axis=1, value=.9), ())
        self.event(pygame.JOYAXISMOTION, instance_id=42, axis=1, value=0)
        self.assertEqual(self.event(pygame.JOYAXISMOTION, instance_id=42, axis=1, value=.8), ('down',))
        self.assertEqual(self.event(pygame.JOYBUTTONDOWN, instance_id=42, button=0), ('confirm',))
        self.assertEqual(self.event(pygame.JOYBUTTONDOWN, instance_id=42, button=2), ('shield',))
        self.assertEqual(set(self.event(pygame.KEYDOWN, key=pygame.K_SPACE)), {'continue', 'shield'})

    def test_instance_id_removal_focus_and_reconnection(self):
        self.pad.axes = [1, 0]
        self.event(pygame.WINDOWFOCUSLOST)
        self.assertEqual(self.manager.sample(self.keys).direction, (0, 0))
        self.event(pygame.WINDOWFOCUSGAINED)
        self.assertEqual(self.manager.sample(self.keys).direction, (1, 0))
        self.event(pygame.JOYDEVICEREMOVED, instance_id=42)
        self.assertTrue(self.pad.closed)
        self.assertTrue(self.manager.disconnected)
        self.assertEqual(self.manager.sample(self.keys).direction, (0, 0))
        self.event(pygame.JOYDEVICEADDED, device_index=0)
        self.assertIn(42, self.manager.devices)

    def test_unknown_device_events_cannot_trigger_actions(self):
        self.assertEqual(self.event(pygame.JOYBUTTONDOWN, instance_id=123, button=0), ())
        self.manager.close()
        self.assertTrue(self.pad.closed)
        self.assertEqual(self.manager.devices, {})
