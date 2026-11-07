"""Controller delle schermate; nessuna I/O di classifica nel tick fisico."""

from uuid import uuid4
import pygame

from game_state import GameState
from highscores import JsonScoreStore, ScoreEntry, ScoreStoreError, normalize_name
from hud import HudData
from manifest import MANIFEST
from controls import KEYS

TEXT = MANIFEST['ui']['strings']


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

    def draw(self, title, lines=(), *, selected=None, footer='', background=False):
        colors = MANIFEST['colors']
        if background:
            shade = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
            shade.fill((*colors['menu_background'], 225))
            self.surface.blit(shade, (0, 0))
        else:
            self.surface.fill(colors['menu_background'])
        self._line(title, MANIFEST['ui']['title_y'], colors['accent'], title=True)
        for index, line in enumerate(lines):
            active = selected == index
            self._line(('> ' if active else '') + line,
                       MANIFEST['ui']['body_y'] + index * MANIFEST['ui']['line_height'],
                       colors['accent'] if active else colors['text'])
        if footer:
            self._line(footer, self.surface.get_height() - 60, colors['accent'])


class CampaignApp:
    def __init__(self, surface, game_factory, *, store=None):
        self.surface = surface
        self.game_factory = game_factory
        self.store = store if store is not None else JsonScoreStore()
        self.game = None  # Nessun livello o stream audio avviato al menu.
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

    @property
    def state(self):
        return self.game.state if self._state == GameState.PLAYING else self._state

    def _menu(self):
        pygame.key.stop_text_input()
        if self.game is not None:
            self.game._resume_audio()
            self.game._stop_draw_audio()
            self.game._cancel_capture()
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.game = None
        self._state = GameState.MENU
        self.message = ''

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
        self._state = GameState.NAME_ENTRY
        self.name = ''
        self.message = ''
        pygame.key.start_text_input()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            if self.game is not None:
                self.game.pause()
            return
        if event.type == pygame.TEXTINPUT and self.state == GameState.NAME_ENTRY:
            limit = MANIFEST['leaderboard']['name_max_chars']
            self.name = (self.name + ''.join(char for char in event.text
                         if char.isalnum() or char in ' _-'))[:limit]
            return
        if event.type != pygame.KEYDOWN:
            return
        key, state = event.key, self.state
        if state == GameState.MENU:
            if key == KEYS['up']:
                self.selected = (self.selected - 1) % len(TEXT['menu_items'])
            elif key == KEYS['down']:
                self.selected = (self.selected + 1) % len(TEXT['menu_items'])
            elif key == KEYS['confirm']:
                if self.selected == 0:
                    self.game = self.game_factory(self.surface)
                    self.run_id = str(uuid4())
                    self._won = False
                    self._state = GameState.PLAYING
                elif self.selected == 1:
                    self.message = ''
                    self._scores()
                else:
                    self.running = False
            elif key in (KEYS['back'], KEYS['quit']):
                self.running = False
        elif state == GameState.HIGHSCORES:
            if key == KEYS['back']:
                self._menu()
            elif key == KEYS['confirm']:
                if self._scores_failed:
                    self.message = ''
                    self._scores()
                else:
                    self._menu()
        elif state == GameState.NAME_ENTRY:
            if key == KEYS['back']:
                self._menu()
            elif key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif key == KEYS['confirm']:
                try:
                    entry = ScoreEntry.create(self.run_id, normalize_name(self.name),
                        self.game.run_score, len(self.game.run.results),
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
            if key in (KEYS['confirm'], KEYS['continue']):
                self._name_entry()
        elif state == GameState.LEVEL_CLEAR:
            if key in (KEYS['confirm'], KEYS['continue']):
                self.game.next_level()
        else:
            if key in (KEYS['pause'], KEYS['back']):
                self.game.toggle_pause()
            elif key == KEYS['restart'] and state == GameState.PHYSICS_ERROR:
                self.game.start_level()
            elif key == KEYS['quit']:
                self.running = False

    def advance(self, keys=None):
        if self._state == GameState.PLAYING:
            self.game.advance_frame(keys)
            if self.game.state == GameState.GAME_OVER:
                self._name_entry()
            elif self.game.state == GameState.CAMPAIGN_COMPLETE:
                self._won = True
                self._state = GameState.CAMPAIGN_COMPLETE

    def draw(self):
        state = self.state
        if state == GameState.MENU:
            self.renderer.draw(TEXT['menu_title'], TEXT['menu_items'],
                               selected=self.selected, footer=TEXT['navigation'])
        elif state == GameState.HIGHSCORES:
            lines = [TEXT['score_row'].format(rank=index, name=entry.name, score=entry.score)
                     for index, entry in enumerate(self.entries, 1)]
            self.renderer.draw(TEXT['scores_title'], lines or [TEXT['scores_empty']],
                               footer=self.message or TEXT['back'])
        elif state in (GameState.NAME_ENTRY, GameState.CAMPAIGN_COMPLETE):
            title = TEXT['complete_title'] if self._won else TEXT['game_over_title']
            lines = [TEXT['run_score'].format(score=self.game.run_score),
                     TEXT['completed_levels'].format(levels=len(self.game.run.results))]
            if state == GameState.NAME_ENTRY:
                lines += [TEXT['enter_name'], self.name + '_']
            self.renderer.draw(title, lines,
                footer=self.message or (TEXT['name_help'] if state == GameState.NAME_ENTRY else TEXT['continue']))
        else:
            self.game.draw()
            if state == GameState.LEVEL_CLEAR:
                result = self.game.level_result
                self.renderer.draw(TEXT['summary_title'].format(level=result.level),
                    [TEXT['summary_capture'].format(percent=result.percent, lives=result.lives),
                     TEXT['summary_base'].format(base=result.base),
                     TEXT['summary_bonus'].format(bonus=result.bonus),
                     TEXT['summary_level_total'].format(score=result.score),
                     TEXT['run_score'].format(score=self.game.run_score),
                     TEXT['summary_time'].format(seconds=result.elapsed_ms // 1000)],
                    footer=TEXT['continue'], background=True)

    def hud_data(self):
        return self.game.hud_data() if self.game is not None else HudData(0, 0, 0, 0, 0, 0, '')

    def close(self):
        self._menu()
