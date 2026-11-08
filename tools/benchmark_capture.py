r"""Costo CPU per frame della cattura con rendering/HUD di produzione (SDL dummy).

Eseguire dalla root con .venv\Scripts\python.exe tools/benchmark_capture.py
Non attende il refresh: separa costo CPU e durata prevista a 60 FPS.
"""

import contextlib
import io
import json
import os
from pathlib import Path
import statistics
import sys
from time import perf_counter_ns

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from game_state import GameState
from hud import Hud
from Upqix89 import Game, WIDTH, HEIGHT, VIEWPORT_SIZE, ROWS
from viewport import Viewport


def measure(cut_x, boss_x):
    window = pygame.display.set_mode(VIEWPORT_SIZE)
    hud = Hud(1024)
    viewport = Viewport(window, (WIDTH, HEIGHT), area=hud.game_area)
    with contextlib.redirect_stdout(io.StringIO()):
        game = Game(viewport.surface, time_source=lambda: 0)
    try:
        for _ in range(10):
            game.draw()
            viewport.present(lambda target: hud.draw(target, game.hud_data()))
        game.enemy_x = boss_x
        game.player_x, game.player_y = cut_x, ROWS - 2
        game.current_trail = [(cut_x, y) for y in range(1, ROWS - 1)]
        game.drawing = True
        start = perf_counter_ns()
        game.fill_area()
        request_ms = (perf_counter_ns() - start) / 1_000_000
        work, frames = [], []
        while game.state == GameState.CAPTURING:
            start = perf_counter_ns()
            game.advance_frame()
            work.append((perf_counter_ns() - start) / 1_000_000)
            game.draw()
            viewport.present(lambda target: hud.draw(target, game.hud_data()))
            frames.append((perf_counter_ns() - start) / 1_000_000)
        assert game.physics_error is None
        assert not game.collision_grid.is_blocked(game._boss_body())
        ordered = sorted(frames)
        return {'cut_column': cut_x, 'capture_frames': len(frames),
                'duration_at_60fps_ms': round(len(frames) * 1000 / 60, 3),
                'request_ms': round(request_ms, 3),
                'work_max_ms': round(max(work), 3),
                'frame_cpu_median_ms': round(statistics.median(frames), 3),
                'frame_cpu_p95_ms': round(ordered[min(len(ordered)-1, int(len(ordered)*0.95))], 3),
                'frame_cpu_max_ms': round(max(frames), 3),
                'score': game.score, 'percent': round(game.percent, 3),
                'final_state': game.state.name}
    finally:
        game._stop_draw_audio()


if __name__ == '__main__':
    pygame.init()
    try:
        # Il caso stretto lascia almeno 160 px al boss largo fino a 134 px.
        print(json.dumps([measure(200, 200), measure(80, 80)], indent=2))
    finally:
        pygame.quit()
