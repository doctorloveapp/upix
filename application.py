"""Controller delle schermate; nessuna I/O di classifica nel tick fisico."""

from uuid import uuid4
import pygame

from game_state import GameState
from highscores import JsonScoreStore, ScoreEntry, ScoreStoreError, normalize_name
from hud import HudData
from manifest import MANIFEST, ROOT
from input_manager import InputManager
from localization import I18N, tr
from debug_menu import CheatSequence, StartSettings
from music import MenuMusic, MusicPlayer

TEXT = I18N


class ScreenRenderer:
    def __init__(self, surface):
        self.surface = surface
        font = MANIFEST['assets']['font']
        self.font = pygame.font.SysFont(font, MANIFEST['ui']['font_size'], bold=True)
        self.title_font = pygame.font.SysFont(font, MANIFEST['ui']['title_font_size'], bold=True)

    def _line(self, label, y, color, title=False):
        text = (self.title_font if title else self.font).render(label, True, color)
        maximum = self.surface.get_width() * 0.9
        if text.get_width() > maximum:
            scale = maximum / text.get_width()
            text = pygame.transform.smoothscale(text, (round(maximum), round(text.get_height() * scale)))
        self.surface.blit(text, text.get_rect(midtop=(self.surface.get_width() // 2, y)))

    def draw(self, title, lines=(), *, selected=None, footer='', background=False, panel=False):
        colors = MANIFEST['colors']
        if background:
            shade = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
            shade.fill((*colors['menu_background'], 225))
            self.surface.blit(shade, (0, 0))
        else:
            self.surface.fill(colors['menu_background'])
        if panel:
            bounds = self.surface.get_rect().inflate(-self.surface.get_width() // 10,
                                                     -self.surface.get_height() * 3 // 10)
            pygame.draw.rect(self.surface, colors['menu_background'], bounds, border_radius=12)
            pygame.draw.rect(self.surface, colors['accent'], bounds, width=1, border_radius=12)
        self._line(title, MANIFEST['ui']['title_y'], colors['accent'], title=True)
        for index, line in enumerate(lines):
            active = selected == index
            self._line(('> ' if active else '') + line,
                       MANIFEST['ui']['body_y'] + index * MANIFEST['ui']['line_height'],
                       colors['accent'] if active else colors['text'])
        if footer:
            self._line(footer, self.surface.get_height() - 60, colors['accent'])


class CampaignApp:
    def __init__(self, surface, game_factory, *, store=None, input_manager=None, music_player=None,
                 menu_music=None):
        self.surface = surface
        self.game_factory = game_factory
        self.store = store if store is not None else JsonScoreStore()
        self.game = None  # La simulazione viene creata soltanto dopo il fade del menu.
        self.input = input_manager if input_manager is not None else InputManager()
        self.music = music_player if music_player is not None else MusicPlayer(
            ROOT / MANIFEST['assets']['root'] / MANIFEST['assets']['music_dir'],
            volume=MANIFEST['audio']['music_volume'], extensions=MANIFEST['audio']['music_extensions'])
        audio = MANIFEST['audio']
        self.menu_music = menu_music if menu_music is not None else MenuMusic(
            ROOT / MANIFEST['assets']['root'] / MANIFEST['assets']['menu_music'],
            volume=audio['menu_music_volume'], fade_in_ms=audio['menu_fade_in_ms'],
            fade_out_ms=audio['menu_fade_out_ms'])
        self._pending_start = None
        self.cheat = CheatSequence(MANIFEST['debug_menu']['sequence'])
        self.debug_settings = StartSettings()
        self.debug_selected = 0
        self._state = GameState.MENU
        self.renderer = ScreenRenderer(surface)
        self.selected = 0
        self.running = True
        self.entries = []
        self.message = ''
        self.name = ''
        self.run_id = None
        self._won = False
        self._scores_failed = False
        self.cycle_selected = 0
        self._enter_menu_music()

    @property
    def state(self):
        return self.game.state if self._state == GameState.PLAYING else self._state

    @property
    def starting_campaign(self):
        return self._pending_start is not None

    def _enter_menu_music(self):
        if not self.menu_music.active:
            self.music.stop()
        self.menu_music.start()

    def _menu(self, *, play_music=True):
        self._pending_start = None
        pygame.key.stop_text_input()
        if self.game is not None:
            self.game._resume_audio()
            self.game._stop_draw_audio()
            self.game._cancel_capture()
            self.game.cancel_death()
        self.game = None
        self.cheat.reset()
        self._state = GameState.MENU
        self.message = ''
        if play_music:
            self._enter_menu_music()
        else:
            self.menu_music.stop()
            self.music.stop()

    def _start_campaign(self, options=None):
        if self.starting_campaign:
            return
        self._pending_start = options if options is not None else StartSettings()
        self.menu_music.fade_out()
        if not self.menu_music.active:
            self._launch_campaign()

    def _launch_campaign(self):
        options = self._pending_start
        self._pending_start = None
        arguments = {'music_player': self.music}
        if options is not None:
            arguments['start_options'] = options
        self.game = self.game_factory(self.surface, **arguments)
        self.run_id = str(uuid4())
        self._won = False
        self.cheat.reset()
        self._state = GameState.PLAYING
        if not self.input.focused:
            self.game.pause()

    def _scores(self):
        pygame.key.stop_text_input()
        self._state = GameState.HIGHSCORES
        self._scores_failed = False
        try:
            self.entries = self.store.load()
        except ScoreStoreError:
            self.entries = []
            self._scores_failed = True
            self.message = TEXT['scores_error']

    def _name_entry(self):
        self._enter_menu_music()
        self._state = GameState.NAME_ENTRY
        self.name = ''
        self.message = ''
        pygame.key.start_text_input()

    def handle_event(self, event):
        actions = self.input.handle_event(event)
        if self.input.disconnected:
            if self.game is not None:
                self.game.dx = self.game.dy = 0
            self.input.disconnected = False
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.cheat.reset()
            if self.game is not None:
                self.game.pause()
            return
        if self.starting_campaign:
            if 'back' in actions:
                self._pending_start = None
                self.menu_music.start()
            elif 'quit' in actions:
                self.running = False
            return
        if event.type == pygame.TEXTINPUT and self.state == GameState.NAME_ENTRY:
            limit = MANIFEST['leaderboard']['name_max_chars']
            self.name = (self.name + ''.join(char for char in event.text
                         if char.isalnum() or char in ' _-'))[:limit]
            return
        if not actions:
            return
        state = self.state
        if state == GameState.MENU:
            token = next((name for name in ('up', 'down', 'left', 'right', 'shield') if name in actions), None)
            if not getattr(event, 'repeat', False) and self.cheat.feed(token):
                self.debug_selected = 0
                self.cheat.reset()
                self._state = GameState.DEBUG_MENU
                return
            if 'up' in actions:
                self.selected = (self.selected - 1) % len(TEXT['menu_items'])
            elif 'down' in actions:
                self.selected = (self.selected + 1) % len(TEXT['menu_items'])
            elif 'confirm' in actions:
                selected = MANIFEST['ui']['menu_actions'][self.selected]
                if selected == 'start':
                    self._start_campaign()
                elif selected == 'scores':
                    self.message = ''
                    self._scores()
                elif selected == 'tutorial':
                    self._state = GameState.TUTORIAL
                elif selected == 'language':
                    I18N.toggle()
                else:
                    self.running = False
            elif 'back' in actions or 'quit' in actions:
                self.running = False
        elif state == GameState.DEBUG_MENU:
            if 'up' in actions:
                self.debug_selected = (self.debug_selected - 1) % 3
            elif 'down' in actions:
                self.debug_selected = (self.debug_selected + 1) % 3
            elif 'left' in actions or 'right' in actions:
                field = ('level', 'lives', 'shields')[self.debug_selected]
                self.debug_settings = self.debug_settings.adjust(field, 1 if 'right' in actions else -1)
            elif 'confirm' in actions:
                self._start_campaign(self.debug_settings)
            elif 'back' in actions:
                self.cheat.reset()
                self._state = GameState.MENU
        elif state == GameState.TUTORIAL:
            if 'back' in actions or 'confirm' in actions:
                self._menu()
        elif state == GameState.HIGHSCORES:
            if 'back' in actions:
                self._menu()
            elif 'confirm' in actions:
                if self._scores_failed:
                    self.message = ''
                    self._scores()
                else:
                    self._menu()
        elif state == GameState.NAME_ENTRY:
            if 'back' in actions:
                self._menu()
            elif 'erase' in actions:
                self.name = self.name[:-1]
            elif 'confirm' in actions:
                try:
                    entry = ScoreEntry.create(self.run_id, normalize_name(self.name),
                        self.game.run_score, self.game.run.completed_count,
                        self.game.run_elapsed_ms, self._won)
                    self.store.submit(entry)
                except ScoreStoreError:
                    self.message = TEXT['storage_error']
                except ValueError:
                    self.message = TEXT['invalid_name']
                else:
                    self.message = TEXT['saved']
                    self._scores()
        elif state == GameState.CAMPAIGN_COMPLETE:
            if 'up' in actions or 'down' in actions:
                self.cycle_selected = 1 - self.cycle_selected
            elif 'confirm' in actions or 'continue' in actions:
                if self.cycle_selected == 0:
                    self.game.continue_cycle()
                    self._state = GameState.PLAYING
                else:
                    self._name_entry()
        elif state == GameState.LEVEL_CLEAR:
            if 'confirm' in actions or 'continue' in actions:
                if self.game.level_rewards_pending:
                    self.game.dismiss_level_rewards()
                else:
                    self.game.next_level()
        else:
            if 'pause' in actions or 'back' in actions:
                self.game.toggle_pause()
            elif 'shield' in actions:
                self.game.request_shield()
            elif 'restart' in actions and state == GameState.PHYSICS_ERROR:
                self.game.start_level()
            elif 'quit' in actions:
                self.running = False

    def advance(self, keys=None):
        if self.starting_campaign:
            self.menu_music.update()
            if not self.menu_music.active:
                self._launch_campaign()
            return
        if self._state == GameState.PLAYING:
            frame = keys if keys is not None else self.input.sample()
            self.game.advance_frame(frame)
            if self.game.state == GameState.GAME_OVER:
                self._name_entry()
            elif self.game.state == GameState.CAMPAIGN_COMPLETE:
                self._won = True
                self._state = GameState.CAMPAIGN_COMPLETE
                self.cycle_selected = 0
        else:
            if self.menu_music.active:
                self.menu_music.update()
            else:
                self.music.update()

    def draw(self):
        state = self.state
        if state == GameState.MENU:
            self.renderer.draw(TEXT['menu_title'], TEXT['menu_items'],
                               selected=self.selected, footer=TEXT['navigation'])
        elif state == GameState.DEBUG_MENU:
            self.renderer.draw(TEXT['menu_title'], TEXT['menu_items'], selected=self.selected)
            self.renderer.draw(TEXT['debug_title'],
                [tr('debug_' + field, value=getattr(self.debug_settings, field))
                 for field in ('level', 'lives', 'shields')],
                selected=self.debug_selected, footer=TEXT['debug_help'], background=True, panel=True)
        elif state == GameState.TUTORIAL:
            lines = [line.format(lives=MANIFEST['engine']['initial_lives'],
                                 extra=MANIFEST['progression']['extra_life_percent'],
                                 shield=MANIFEST['shields']['capture_percent'])
                     for line in TEXT['tutorial_lines']]
            self.renderer.draw(TEXT['tutorial_title'], lines, footer=TEXT['back'])
        elif state == GameState.HIGHSCORES:
            lines = [TEXT['score_row'].format(rank=index, name=entry.name, score=entry.score)
                     for index, entry in enumerate(self.entries, 1)]
            self.renderer.draw(TEXT['scores_title'], lines or [TEXT['scores_empty']],
                               footer=self.message or TEXT['back'])
        elif state in (GameState.NAME_ENTRY, GameState.CAMPAIGN_COMPLETE):
            title = TEXT['complete_title'] if self.game.state == GameState.CAMPAIGN_COMPLETE else TEXT['game_over_title']
            lines = [TEXT['run_score'].format(score=self.game.run_score),
                     TEXT['completed_levels'].format(levels=self.game.run.completed_count)]
            if state == GameState.NAME_ENTRY:
                lines += [TEXT['enter_name'], self.name + '_']
            else:
                lines += [line.format(cycle=self.game.cycle + 1) for line in TEXT['cycle_options']]
            self.renderer.draw(title, lines,
                selected=(2 + self.cycle_selected) if state == GameState.CAMPAIGN_COMPLETE else None,
                footer=self.message or (TEXT['name_help'] if state == GameState.NAME_ENTRY else TEXT['continue']))
        else:
            self.game.draw()
            if state == GameState.LEVEL_CLEAR:
                result = self.game.level_result
                if self.game.level_rewards_pending:
                    self.renderer.draw(tr('rewards_title'), footer=TEXT['rewards_continue'], background=True)
                    self.game.draw_level_rewards()
                    return
                self.renderer.draw(TEXT['summary_title'].format(level=result.level, cycle=result.cycle),
                    [TEXT['summary_capture'].format(percent=result.percent, lives=result.lives),
                     TEXT['summary_base'].format(base=result.base),
                     TEXT['summary_bonus'].format(bonus=result.bonus),
                     TEXT['summary_level_total'].format(score=result.score),
                     TEXT['run_score'].format(score=self.game.run_score),
                     TEXT['summary_time'].format(seconds=result.elapsed_ms // 1000),
                     tr('summary_extra_life' if result.extra_life else 'summary_no_extra',
                        lives=result.extra_life, threshold=MANIFEST['progression']['extra_life_percent']),
                     tr('summary_shields', earned=result.shields_earned, shields=self.game.shields.charges)],
                    footer=TEXT['continue'], background=True)

    def hud_data(self):
        return self.game.hud_data() if self.game is not None else HudData(0, 0, 0, 0, 0, 0, '')

    def close(self):
        self._menu(play_music=False)
        self.debug_settings = StartSettings()
        self.input.close()
