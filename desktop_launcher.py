"""Ingresso della release Windows; risorse incluse, salvataggi fuori dal bundle."""

import json
import os
from pathlib import Path
import sys
import traceback


def smoke_test(output):
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    import pygame
    from application import CampaignApp
    from audio_normalization import configured_normalizer
    from debug_menu import StartSettings
    from game_state import GameState
    from highscores import JsonScoreStore, ScoreEntry
    from hud import Hud
    from input_manager import InputFrame
    from localization import I18N
    from manifest import MANIFEST, ROOT
    from music import MenuMusic
    from Upqix89 import Game
    from viewport import Viewport

    now = 0
    pygame.init()
    window = pygame.display.set_mode(MANIFEST['engine']['window_size'])
    hud = Hud(*MANIFEST['engine']['window_size'])
    viewport = Viewport(window, MANIFEST['engine']['logical_size'], area=hud.game_area)
    menu = MenuMusic(ROOT / MANIFEST['assets']['root'] / MANIFEST['assets']['menu_music'],
                     volume=.26, fade_in_ms=0, fade_out_ms=0, time_source=lambda: now)
    app = CampaignApp(viewport.surface,
        lambda surface, **kwargs: Game(surface, time_source=lambda: now, **kwargs), menu_music=menu)
    try:
        assert app.state == GameState.MENU
        app.draw()
        app._start_campaign(StartSettings(level=12, lives=15))
        game = app.game
        assert game.boss_img is not None and game.cursor_img is not None
        assert all(frame is not None for frame in game.death_frames)
        game.handle_death()
        assert game.state == GameState.DYING and game.lives == 14
        for _ in range(100):
            if game.state != GameState.DYING:
                break
            now += 17
            app.advance(InputFrame())
            app.draw()
        assert game.state == GameState.PLAYING
        game.percent = 90
        game._set_state(GameState.LEVEL_CLEAR)
        game.dismiss_level_rewards()
        game.next_level()
        app.advance(InputFrame())
        assert app.state == GameState.CAMPAIGN_COMPLETE
        for language in ('it', 'en'):
            I18N.set_language(language)
            app.draw()
        viewport.present(lambda target: hud.draw(target, app.hud_data()))
        pygame.image.save(window, str(output.with_suffix('.png')))
        store = JsonScoreStore()
        entry = ScoreEntry.create('00000000-0000-0000-0000-000000000089', 'Smoke',
                                  game.run_score, game.run.completed_count, game.run_elapsed_ms, True)
        store.submit(entry)
        assert any(item.run_id == entry.run_id for item in store.load())
        normalizer = configured_normalizer()
        sources = [ROOT / MANIFEST['assets']['root'] / MANIFEST['assets'][key]
                   for key in ('first_level_music', 'menu_music')]
        assert all(normalizer.resolve(path) != path for path in sources)
        output.write_text(json.dumps(dict(
            ok=True, frozen=getattr(sys, 'frozen', False), state=app.state.name,
            saved_to=str(store.path), manifest=str(ROOT), audio_cache=True,
            boss_size=game.boss_size, player_size=game.player_sprite_size), indent=2), encoding='utf-8')
    finally:
        app.close()
        pygame.quit()


def main():
    output = None
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        output = Path(sys.argv[2]).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or sys.stderr is None:
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'UPIX1989'
        base.mkdir(parents=True, exist_ok=True)
        log = open(base / 'launcher.log', 'w', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = log
    try:
        if output is not None:
            smoke_test(output)
        else:
            from Upqix89 import main as run_game
            run_game()
    except Exception:
        traceback.print_exc()
        if output is not None:
            output.write_text(json.dumps(dict(ok=False, error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
