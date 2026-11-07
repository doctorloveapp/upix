"""Associazioni configurate, senza inizializzare SDL durante l'import."""

import pygame
from manifest import MANIFEST


def key_bindings():
    try:
        return {name: getattr(pygame, 'K_' + (value if len(value) == 1 else value.upper()))
                for name, value in MANIFEST['controls'].items()}
    except AttributeError as exc:
        raise ValueError('Tasto manifest non supportato') from exc


KEYS = key_bindings()
