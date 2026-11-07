r"""Misura le funzioni di produzione a risoluzioni selezionate, senza cambiare i sorgenti.

Eseguire dalla root: .venv\Scripts\python.exe tools/benchmark_resolution.py
I tempi non sono test con soglie: dipendono dall'hardware e dal carico del PC.
"""

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import statistics
import sys
import time
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
import Upqix89 as upix
from collisions import move_body
from territory import plan_capture


def measure(width, height, repeats):
    screen = pygame.display.set_mode((width, height))
    cols, rows = width // upix.CELL_SIZE, height // upix.CELL_SIZE
    planning, capture, motion = [], [], []
    with mock.patch.multiple(upix, WIDTH=width, HEIGHT=height, COLS=cols, ROWS=rows):
        with contextlib.redirect_stdout(io.StringIO()):
            game = upix.Game(screen)
        for _ in range(repeats):
            with contextlib.redirect_stdout(io.StringIO()):
                game.start_level()
            game.enemy_x, game.enemy_y = width / 4, height / 2
            game.current_trail = [(cols // 2, y) for y in range(1, rows - 1)]
            game.player_x, game.player_y = cols // 2, rows - 2
            game.drawing = True
            start = time.perf_counter()
            plan_capture(game.collision_grid, game.current_trail, game._boss_body())
            planning.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            game.fill_area()
            capture.append((time.perf_counter() - start) * 1000)
            assert not game.physics_error
        for _ in range(100):
            start = time.perf_counter()
            move_body(game.collision_grid, game._boss_body(), 6.6, 3.3)
            motion.append((time.perf_counter() - start) * 1000)
        surfaces = sum(image.get_pitch() * image.get_height()
                       for image in (screen, game.canvas, game.hidden_image))
        game._stop_draw_audio()
    return {"resolution": [width, height], "cells": cols * rows,
            "capture_samples_ms": [round(value, 3) for value in capture],
            "planning_median_ms": round(statistics.median(planning), 3),
            "capture_median_ms": round(statistics.median(capture), 3),
            "boss_step_median_ms": round(statistics.median(motion), 3),
            "three_surfaces_MiB": round(surfaces / 1024**2, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--resolutions", nargs="+", default=["800x600", "1024x768", "1024x1024"],
                        choices=["800x600", "1024x768", "1024x1024"])
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats deve essere positivo")
    pygame.init()
    try:
        dimensions = [tuple(map(int, value.split("x"))) for value in args.resolutions]
        results = [measure(w, h, args.repeats) for w, h in dimensions]
        print(json.dumps(results, indent=2))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
