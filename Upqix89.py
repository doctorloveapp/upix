import pygame
import math
import random
from pathlib import Path
from time import perf_counter_ns
from assets import (compose_level_cover, load_animation_frames, load_level_cover,
                    load_level_image, load_sprite)
from campaign import LevelResult, RunScore
from manifest import MANIFEST, ROOT
from collisions import (AABB, CollisionGrid, move_body, move_projectile,
                        move_player, player_cell_allowed, swept_contact)
from game_state import FixedTimestep, GameState, SimulationClock
from shock_system import ShockSystem
from perimeter_threat import PerimeterThreat, build_perimeters
from sprite_renderer import DirectionalSprite
from input_manager import InputFrame, keyboard_direction
from localization import I18N, tr
from shields import Shields
from scoring import LevelScore
from territory import CaptureContactError, CapturePlanner
from hud import Hud, HudData
from level_config import LEVEL_CONFIGS, get_level_config
from music import MusicPlayer
from debug_menu import StartSettings
from death_sequence import DeathSequence
from viewport import Viewport

# --- CONFIGURAZIONE ---
ENGINE = MANIFEST['engine']
STRINGS = I18N
WIDTH, HEIGHT = ENGINE['logical_size']
VIEWPORT_SIZE = ENGINE['window_size']
RENDER_FPS_LIMIT = ENGINE['render_fps']
CAPTURE_BUDGET_NS = ENGINE['capture_budget_ms'] * 1_000_000
CAPTURE_CHUNK_CELLS = ENGINE['capture_chunk_cells']
CAPTURE_MAX_CHUNKS = ENGINE['capture_max_chunks']
CELL_SIZE = ENGINE['cell_size']
COLS = WIDTH // CELL_SIZE
ROWS = HEIGHT // CELL_SIZE
ASSET_DIR = ROOT / MANIFEST['assets']['root']
MUSIC_VOLUME = MANIFEST['audio']['music_volume']
DRAW_MUSIC_ATTENUATION = MANIFEST['audio']['drawing_attenuation']
DRAW_MUSIC_VOLUME = MUSIC_VOLUME - DRAW_MUSIC_ATTENUATION
DRAW_VOLUME = MANIFEST['audio']['welding_volume']
BOSS_SIZE = LEVEL_CONFIGS[0].boss_max_size
MISSILE_COLLISION_SIZE = ENGINE['missile_collision_size'] * ENGINE['missile_size_scale']
MISSILE_RENDER_RADIUS = round(ENGINE['missile_render_radius'] * ENGINE['missile_size_scale'])
PLAYER_SPRITE_SIZE = ENGINE['player_max_size']

# Colori
COLOR_BG_COVER = MANIFEST['colors']['cover']
COLOR_PLAYER = MANIFEST['colors']['player']
COLOR_TRAIL = MANIFEST['colors']['trail']
COLOR_ENEMY = MANIFEST['colors']['enemy']

# Stati
EMPTY = ENGINE['empty_cell']
FILLED = ENGINE['filled_cell']

class Game:
    def __init__(self, screen, *, time_source=None, rng=None, music_player=None, start_options=None):
        self.screen = screen
        self.font = pygame.font.SysFont(MANIFEST['assets']['font'], MANIFEST['ui']['font_size'], bold=True)
        self.run = RunScore()
        self.cycle = 1
        self.shields = Shields(MANIFEST['shields'], ENGINE['simulation_hz'])
        self._shield_requested = False
        self.level_result = None
        self.level_rewards_pending = False
        self.state = GameState.PLAYING
        self.game_clock = SimulationClock()
        self.frame_clock = FixedTimestep(time_source)
        self.rng = rng if rng is not None else random.Random()
        self._resume_state = GameState.PLAYING
        self._capture_work = None
        self._capture_canvas = None
        self._capture_grid = None
        # --- AUDIO SETUP ---
        self.sound_draw = None
        self.draw_channel = None
        self.death_sound = None
        self.death_channel = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            # Canali riservati: 0 saldatrice, 1 esplosione.
            pygame.mixer.set_reserved(2)
            self.draw_channel = pygame.mixer.Channel(0)
            self.death_channel = pygame.mixer.Channel(1)
            self.death_channel.stop()
            self.draw_channel.stop()
            # WAV pronto per effetti brevi; l'MP3 originale resta un fallback.
            for filename in MANIFEST['assets']['welding_sounds']:
                sound_path = ASSET_DIR / filename
                try:
                    self.sound_draw = pygame.mixer.Sound(str(sound_path))
                    self.sound_draw.set_volume(DRAW_VOLUME)
                    break
                except (pygame.error, OSError) as exc:
                    print(f"Effetto audio non disponibile ({sound_path}): {exc}")
            try:
                self.death_sound = pygame.mixer.Sound(str(ASSET_DIR / MANIFEST['assets']['death_sound']))
                self.death_sound.set_volume(MANIFEST['death_sequence']['sound_volume'])
            except (pygame.error, OSError) as exc:
                print(f"Audio esplosione non disponibile: {exc}")
        except pygame.error as exc:
            print(f"Audio disabilitato: {exc}")

        # Carica Cursore
        self.cursor_img, self.player_sprite_size = load_sprite(
            ASSET_DIR / MANIFEST['assets']['player_sprite'], PLAYER_SPRITE_SIZE)
        death = MANIFEST['death_sequence']
        self.death_frames = load_animation_frames(
            (ASSET_DIR / path for path in MANIFEST['assets']['death_frames']),
            self.player_sprite_size, death['sprite_scale'])
        self.death_sequence = DeathSequence(len(self.death_frames), death['frame_duration_ms'],
                                           ENGINE['simulation_hz'])
        energy_path = ASSET_DIR / MANIFEST['assets']['energy_sprite']
        self.missile_visual = DirectionalSprite(
            energy_path, (MISSILE_RENDER_RADIUS * 2,) * 2, MANIFEST['energy_visual'])
        self.threat_visual = DirectionalSprite(
            energy_path, MANIFEST['perimeter_threat']['sprite_max_size'], MANIFEST['energy_visual'])
        self.shield_notice_img, _ = load_sprite(
            ASSET_DIR / MANIFEST['assets']['shield_sprite'], MANIFEST['shields']['notice_sprite_size'])
        self.life_notice_img, _ = load_sprite(
            ASSET_DIR / MANIFEST['assets']['life_sprite'], MANIFEST['shields']['notice_sprite_size'])

        self.music = music_player if music_player is not None else MusicPlayer(
            ASSET_DIR / MANIFEST['assets']['music_dir'], volume=MUSIC_VOLUME,
            extensions=MANIFEST['audio']['music_extensions'])

        # Livelli
        options = start_options if start_options is not None else StartSettings()
        self.level = options.level
        self.max_levels = len(LEVEL_CONFIGS)
        self.lives = options.lives
        self.shields.charges = options.shields
        
        self.start_level()

    def _load_boss_sprite(self):
        """Carica lo sprite RGBA proporzionato e determina l'ingombro grafico/fisico."""
        boss_path = ASSET_DIR / MANIFEST['assets']['boss_dir'] / self.level_config.boss_sprite
        image, self.boss_size = load_sprite(boss_path, self.level_config.boss_max_size,
                                            self.level_config.boss_render_scale)
        return image

    @property
    def game_over(self):
        return self.state == GameState.GAME_OVER

    @property
    def win(self):
        return self.state == GameState.LEVEL_CLEAR

    @property
    def score(self):
        return self.level_score.total(self.game_clock.elapsed_ms)

    @property
    def run_score(self):
        return self.run.total(self.level, self.score, self.cycle)

    @property
    def perimeter_threat(self):
        """Vista compatibile del primo elemento; la lista è l'unica sorgente."""
        return self.perimeter_threats[0] if self.perimeter_threats else None

    @perimeter_threat.setter
    def perimeter_threat(self, value):
        self.perimeter_threats = [] if value is None else [value]

    @property
    def run_elapsed_ms(self):
        return self.run.elapsed_ms + (0 if self.level_result else self.game_clock.elapsed_ms)

    def _set_state(self, state: GameState):
        if self.state == state:
            return
        previous = self.state
        self.state = state
        self.frame_clock.reset()
        if state == GameState.PLAYING:
            self.game_clock.resume()
            if previous in (GameState.PAUSED, GameState.DYING):
                self._resume_audio()
            self._sync_draw_audio()
        else:
            self.game_clock.pause()
            if state == GameState.LEVEL_CLEAR:
                extra = 0
                if not self.run.has_result(self.level, self.cycle):
                    extra = int(self.percent >= MANIFEST['progression']['extra_life_percent'])
                    self.lives += extra
                    self.level_rewards_pending = bool(extra or self.shields.earned_this_level)
                self.level_result = self.run.complete(LevelResult(
                    self.level, self.level_score.base_points,
                    self.level_score.bonus(self.game_clock.elapsed_ms),
                    self.game_clock.elapsed_ms, self.percent, self.lives,
                    self.cycle, extra, self.shields.earned_this_level))
            if state == GameState.PAUSED:
                if pygame.mixer.get_init():
                    pygame.mixer.pause()
                    pygame.mixer.music.pause()
            else:
                if previous == GameState.PAUSED:
                    self._resume_audio()
                elif previous == GameState.DYING:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.unpause()
                self._stop_draw_audio()
                if state == GameState.DYING and pygame.mixer.get_init():
                    pygame.mixer.music.pause()

    def _resume_audio(self):
        if pygame.mixer.get_init():
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()

    def pause(self):
        if self.state in (GameState.PLAYING, GameState.CAPTURING, GameState.DYING):
            self._resume_state = self.state
            self._set_state(GameState.PAUSED)

    def toggle_pause(self):
        if self.state == GameState.PAUSED:
            self._set_state(self._resume_state)
        else:
            self.pause()

    def handle_death(self, *, center=None):
        if self.state != GameState.PLAYING:
            return
        if center is None:
            center = ((self.player_x + .5) * CELL_SIZE, (self.player_y + .5) * CELL_SIZE)
        self.death_sequence.start(center)
        self._set_state(GameState.DYING)  # Sospende clock e musica, annulla il recupero.
        if self.death_sound is not None and self.death_channel is not None:
            self.death_channel.play(self.death_sound)
        # Sequenza e audio sono già avviati; le chiamate successive in DYING
        # vengono rifiutate prima di qualunque ulteriore decremento.
        self.lives -= 1
        self._respawn_waiting_for_release = True
        self._shield_requested = False
        print(tr('diagnostic_lives', lives=self.lives))

    def _advance_death(self):
        if self.death_sequence.advance():
            self._finish_death()

    def _finish_death(self):
        """Unico commit dopo l'ultimo frame: pulizia e respawn oppure finale."""
        self.dx = self.dy = 0
        self.drawing = False
        self.current_trail = []
        self.missiles = []
        self.shock.reset()
        self.perimeter_threat = None
        self.shields.on_death()
        self._shield_requested = False
        
        if self.lives > 0:
            # Respawn all'ultima posizione sicura conosciuta
            self.player_x = self.last_safe_x
            self.player_y = self.last_safe_y
            self._set_state(GameState.PLAYING)
        else:
            self._set_state(GameState.GAME_OVER)

    def cancel_death(self):
        self.death_sequence.cancel()
        if self.death_channel is not None:
            self.death_channel.stop()

    def request_shield(self):
        if self.state == GameState.PLAYING:
            self._shield_requested = True

    def _handle_hostile_contact(self, *, center=None):
        if self.state != GameState.PLAYING:
            return
        if self.shields.absorb():
            # Il taglio colpito viene annullato: non si può conquistare un boss
            # che interseca ancora la scia. Nessuna modifica parziale alla griglia.
            if self.drawing:
                self.player_x, self.player_y = self.last_safe_x, self.last_safe_y
            self.current_trail = []
            self.drawing = False
            self.dx = self.dy = 0
            self._stop_draw_audio()
        else:
            self.handle_death(center=center)

    def _stop_draw_audio(self):
        if self.draw_channel is not None:
            self.draw_channel.stop()
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(MUSIC_VOLUME)

    def _sync_draw_audio(self):
        """La saldatrice segue il tracciamento, mai lo spostamento in zona sicura."""
        if self.state == GameState.PAUSED:
            return  # Il canale è sospeso: non fermare o riavviare il campione.
        active = (self.drawing and self.state == GameState.PLAYING
                  and self.grid[self.player_x][self.player_y] == EMPTY)
        if not active or self.sound_draw is None or self.draw_channel is None:
            self._stop_draw_audio()
            return
        if not self.draw_channel.get_busy():
            self.draw_channel.play(self.sound_draw, loops=-1)
        pygame.mixer.music.set_volume(DRAW_MUSIC_VOLUME)

    def _play_music(self):
        self.music.play_level(self.level, ASSET_DIR / MANIFEST['assets']['first_level_music'])

    def start_level(self):
        if self.state in (GameState.PAUSED, GameState.DYING):
            self._resume_audio()
        self.cancel_death()
        self._stop_draw_audio()
        self._cancel_capture()
        self.level_result = None
        self.level_rewards_pending = False
        self.level_config = get_level_config(self.level, self.cycle)
        self.shields.start_level()
        self._shield_requested = False
        self.shock = ShockSystem(self.level_config.shock)
        self.perimeter_threat = None
        self.level_score = LevelScore(self.level_config.scoring, COLS * ROWS)
        self.boss_img = self._load_boss_sprite()
        self._play_music()  # Livello 1 fisso; dal 2 shuffle senza riavvii fra livelli.
        self.physics_error = None
        self.grid = [[EMPTY for _ in range(ROWS)] for _ in range(COLS)]
        self.collision_grid = CollisionGrid(self.grid, CELL_SIZE, FILLED)
        
        # --- CARICAMENTO IMMAGINE LIVELLO ---
        # Format 01.png, 02.png ...
        self.hidden_image, self.primary_image_source = load_level_image(
            ASSET_DIR, self.level, (WIDTH, HEIGHT), source=self.level_config.primary)
        if self.hidden_image is None:
            self.hidden_image = self._create_fallback_image()

        # --- SURFACE DI GIOCO (CANVAS) ---
        # Composizione statica: SVG retinato sopra la primaria appena intravista.
        cover, self.cover_source = load_level_cover(
            ASSET_DIR, self.level, (WIDTH, HEIGHT), source=self.level_config.cover)
        if cover is None:
            self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
            self.canvas.fill(COLOR_BG_COVER)
        else:
            self.canvas = compose_level_cover(self.hidden_image, cover, MANIFEST['level_cover'])
        print(f"Livello {self.level}: immagine={self.primary_image_source or 'procedurale'}, "
              f"copertura={self.cover_source or 'neutra'}")

        # Setup bordi iniziali (sveliamo i bordi dell'immagine)
        border_thick = ENGINE['border_cells']
        self._filled_cells = 0
        for x in range(COLS):
            for y in range(ROWS):
                # Se è un bordo
                if x < border_thick or x >= COLS - border_thick or y < border_thick or y >= ROWS - border_thick:
                    self.grid[x][y] = FILLED
                    self._filled_cells += 1
                    # Sveliamo il pixel sul canvas
                    self._reveal_pixel(x, y)

        # Il caricamento è fuori dal tick fisico; i commit successivi sono cooperativi.
        builder = build_perimeters(self.grid, CELL_SIZE, FILLED)
        while True:
            try:
                next(builder)
            except StopIteration as done:
                self.perimeter_routes = done.value
                break

        self.player_x = COLS // 2
        self.player_y = ROWS - border_thick
        self.last_safe_x = self.player_x
        self.last_safe_y = self.player_y
        self._respawn_waiting_for_release = False
        
        self.dx = 0
        self.dy = 0
        self.drawing = False
        self.current_trail = [] 
        
        self.enemy_x = WIDTH // 2
        self.enemy_y = HEIGHT // 2
        # Magnitudine identica allo spawn e dopo ogni cambio di direzione.
        self.enemy_vx = self.level_config.boss_speed / math.sqrt(2)
        self.enemy_vy = self.enemy_vx
        
        # Boss Behavior
        self.missiles = []
        self.game_clock.reset()
        self.last_shot_time = 0
        self.enemy_change_dir_timer = 0
        self.shoot_interval = self.level_config.missile_interval_ms

        self.state = GameState.PLAYING
        self.percent = self._filled_cells * 100 / (COLS * ROWS)
        # Non simulare il tempo trascorso durante caricamento/rasterizzazione.
        self.frame_clock.reset()

    def next_level(self):
        if self.level >= self.max_levels:
            self._set_state(GameState.CAMPAIGN_COMPLETE)
        else:
            self.level += 1
            self.start_level()

    def continue_cycle(self):
        if self.state != GameState.CAMPAIGN_COMPLETE:
            return
        self.cycle += 1
        self.level = 1
        self.start_level()

    def _create_fallback_image(self):
        # Crea un'immagine arcobaleno se manca il file
        surf = pygame.Surface((WIDTH, HEIGHT))
        for x in range(WIDTH):
            # Gradiente orizzontale
            c = (x % 255, (x * 2) % 255, 150)
            pygame.draw.line(surf, c, (x, 0), (x, HEIGHT))
        return surf

    def _reveal_pixel(self, gx, gy):
        """Copia un pezzetto dall'immagine nascosta al canvas visibile"""
        rect = pygame.Rect(gx * CELL_SIZE, gy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        self.canvas.blit(self.hidden_image, rect, area=rect)

    def get_pixel_rect(self, gx, gy):
        return pygame.Rect(gx * CELL_SIZE, gy * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    def fill_area(self):
        if self.state != GameState.PLAYING:
            return
        self._stop_draw_audio()
        planner = CapturePlanner(self.collision_grid, tuple(self.current_trail), self._boss_body())
        self._capture_work = self._capture_transaction(planner)
        self._set_state(GameState.CAPTURING)

    def _cancel_capture(self):
        self._capture_work = None
        self._capture_canvas = None
        self._capture_grid = None

    def _advance_capture(self):
        """Budget CPU cooperativo: il rendering/event loop continua a ogni frame."""
        deadline = perf_counter_ns() + CAPTURE_BUDGET_NS
        try:
            for _ in range(CAPTURE_MAX_CHUNKS):
                next(self._capture_work)
                if perf_counter_ns() >= deadline:
                    break
        except StopIteration:
            self._cancel_capture()
        except CaptureContactError:
            self._cancel_capture()
            self._set_state(GameState.PLAYING)
            self._handle_hostile_contact()
        except ValueError as exc:
            self._cancel_capture()
            self._halt_physics(exc)

    def _capture_transaction(self, planner):
        while not planner.advance(CAPTURE_CHUNK_CELLS):
            yield
        capture = planner.result
        # Preparazione isolata: nessuna scrittura sulla geometria attiva.
        self._capture_canvas = self.canvas.copy()
        yield
        self._capture_grid = []
        for column in self.grid:
            self._capture_grid.append(column.copy())
            yield
        for x, first, end in capture.spans:
            rect = pygame.Rect(x * CELL_SIZE, first * CELL_SIZE,
                               CELL_SIZE, (end - first) * CELL_SIZE)
            self._capture_grid[x][first:end] = [FILLED] * (end - first)
            self._capture_canvas.blit(self.hidden_image, rect, area=rect)
            yield
        # Anche la ricostruzione del confine rispetta il budget CAPTURING.
        routes = yield from build_perimeters(self._capture_grid, CELL_SIZE, FILLED)
        new_geometry = CollisionGrid(self._capture_grid, CELL_SIZE, FILLED)
        # La nuova conquista può inglobare il punto di chiusura. Torna lungo
        # la linea appena conclusa fino al primo punto del nuovo confine.
        landing = None
        for index, cell in enumerate(reversed(self.current_trail)):
            if (self._capture_grid[cell[0]][cell[1]] == FILLED
                    and player_cell_allowed(new_geometry, *cell)):
                landing = cell
                break
            if index % CAPTURE_CHUNK_CELLS == 0:
                yield
        if landing is None:
            raise ValueError('La conquista non offre un punto di rientro sul confine')
        # Commit per scambio di riferimenti: nessuna fisica vede dati intermedi.
        self.grid = self._capture_grid
        self.perimeter_routes = routes
        self.perimeter_threat = None
        self.collision_grid = CollisionGrid(self.grid, CELL_SIZE, FILLED)
        self.canvas = self._capture_canvas
        self._filled_cells += capture.cell_count
        self.level_score.capture(capture.area_count)
        self.shields.award(capture.cell_count, COLS * ROWS)
        self.shock.reset()
        self.current_trail = []
        self.drawing = False
        self.dx, self.dy = 0, 0
        self.player_x, self.player_y = landing
        self.last_safe_x, self.last_safe_y = self.player_x, self.player_y
        self.percent = self._filled_cells * 100 / (COLS * ROWS)
        self._set_state(GameState.LEVEL_CLEAR if self.percent >= self.level_config.victory_percent
                        else GameState.PLAYING)

    def _boss_body(self):
        return AABB.from_center(self.enemy_x, self.enemy_y, *self.boss_size)

    def _player_body(self):
        return AABB.from_center((self.player_x + .5) * CELL_SIZE,
                                (self.player_y + .5) * CELL_SIZE, *self.player_sprite_size)

    def _halt_physics(self, error):
        self.physics_error = str(error)
        self.dx = self.dy = 0
        self._set_state(GameState.PHYSICS_ERROR)
        print(f"Simulazione sospesa: {self.physics_error}")

    def _move_boss(self):
        trail = frozenset((x, y) for x, y in self.current_trail if self.grid[x][y] == EMPTY)
        player = None
        if self.drawing and self.grid[self.player_x][self.player_y] == EMPTY:
            player = self._player_body()
        try:
            result = move_body(self.collision_grid, self._boss_body(),
                               self.enemy_vx, self.enemy_vy, trail=trail, player=player)
        except ValueError as exc:
            self._halt_physics(exc)
            return False
        self.enemy_x = result.body.left + result.body.width / 2
        self.enemy_y = result.body.top + result.body.height / 2
        self.enemy_vx = 0 if result.locked_x else self.enemy_vx * (-1 if result.reflected_x else 1)
        self.enemy_vy = 0 if result.locked_y else self.enemy_vy * (-1 if result.reflected_y else 1)
        if result.hit is not None:
            self._handle_hostile_contact()
            return False
        return True

    def _new_trail_hits_boss(self):
        body = self._boss_body()
        trail = set(self.current_trail)
        return any(cell in trail and self.grid[cell[0]][cell[1]] == EMPTY
                   and body.overlaps(self.collision_grid.cell_bounds(*cell))
                   for cell in self.collision_grid.candidate_cells(body))

    def _missile_body(self, missile):
        return AABB.from_center(missile['x'], missile['y'],
                                MISSILE_COLLISION_SIZE, MISSILE_COLLISION_SIZE)

    def _safe_player_body(self):
        if not self.drawing and self.grid[self.player_x][self.player_y] == FILLED:
            return self._player_body()
        return None

    def _update_perimeter_threat(self):
        config = MANIFEST['perimeter_threat']
        if not self.shock.active or not config['enabled']:
            self.perimeter_threat = None
            return True
        target = ((self.player_x + 0.5) * CELL_SIZE, (self.player_y + 0.5) * CELL_SIZE)
        if self.perimeter_threat is None:
            count = self.level_config.perimeter_threat_count
            first = PerimeterThreat.spawn(
                self.perimeter_routes, target,
                speed_per_tick=(self.level_config.perimeter_speed_px_per_second * config['speed_multiplier']
                                / ENGINE['simulation_hz']),
                body_size=config['body_size'], fixed_direction=1 if count == 2 else None)
            self.perimeter_threat = first
            if first is not None and count == 2:
                self.perimeter_threats.append(PerimeterThreat(
                    first.route, first.distance, speed_per_tick=first.speed_per_tick,
                    body_size=first.body_size, fixed_direction=-1))
        player = None if self.shields.grace_ticks else self._safe_player_body()
        for threat in self.perimeter_threats:
            if threat.advance(target, player):
                self._handle_hostile_contact()
                return False
        return True

    def _player_touches_perimeter_threat(self):
        player = self._safe_player_body()
        return (player is not None and not self.shields.grace_ticks
                and any(threat.body.overlaps(player) for threat in self.perimeter_threats))

    def _update_missiles(self):
        trail = frozenset((x, y) for x, y in self.current_trail if self.grid[x][y] == EMPTY)
        player = None
        if self.drawing and self.grid[self.player_x][self.player_y] == EMPTY:
            player = self._player_body()
        survivors = []
        try:
            for index, missile in enumerate(self.missiles):
                result = move_projectile(self.collision_grid, self._missile_body(missile),
                                         missile['vx'], missile['vy'], trail=trail, player=player)
                if result.hit == "wall":
                    continue
                if result.hit is not None:
                    self.missiles = survivors + self.missiles[index + 1:]
                    self._handle_hostile_contact()
                    return False
                survivors.append({**missile, 'x': result.body.left + result.body.width / 2,
                                  'y': result.body.top + result.body.height / 2})
        except ValueError as exc:
            self._halt_physics(exc)
            return False
        self.missiles = survivors
        return True

    def _new_trail_hits_missile(self):
        trail = set(self.current_trail)
        for missile in self.missiles:
            body = self._missile_body(missile)
            for cell in self.collision_grid.candidate_cells(body):
                if (cell in trail and self.grid[cell[0]][cell[1]] == EMPTY
                        and body.overlaps(self.collision_grid.cell_bounds(*cell))):
                    return True
        return False

    def advance_frame(self, keys=None):
        """Consuma il tempo reale; input stabile per tutti i tick del frame."""
        self.music.update(paused=self.state in (GameState.PAUSED, GameState.DYING))
        self._sync_draw_audio()
        if self.state == GameState.DYING:
            return self.frame_clock.advance(self._advance_death)
        if self.state == GameState.CAPTURING:
            self._advance_capture()
            return 0
        if self.state != GameState.PLAYING:
            return 0
        if keys is None:
            keys = InputFrame()
        return self.frame_clock.advance(lambda: self.update(keys))

    def update(self, keys=None):
        """Un singolo tick fisso: velocità espresse in pixel/celle per tick."""
        if self.state != GameState.PLAYING:
            return

        self.game_clock.advance()
        self.shields.advance()
        if self._shield_requested:
            self.shields.activate()
            self._shield_requested = False
        current_time = self.game_clock.elapsed_ms
        # Il tempo sicuro include anche il movimento lungo il bordo/territorio.
        # La pressione resta attiva nel taglio, fino a conquista o morte.
        self.shock.advance(safe=not self.drawing
                          and self.grid[self.player_x][self.player_y] == FILLED)
        if not self._update_perimeter_threat():
            return

        # --- BOSS AI ---
        # 1. Movimento Randomico
        config = self.level_config
        if current_time - self.enemy_change_dir_timer >= config.direction_interval_ms:
            self.enemy_change_dir_timer = current_time
            # Aggiunge componente casuale
            self.enemy_vx += self.rng.uniform(-config.direction_jitter, config.direction_jitter)
            self.enemy_vy += self.rng.uniform(-config.direction_jitter, config.direction_jitter)
            if config.pursuit_weight and self.drawing:
                dx = self.player_x * CELL_SIZE - self.enemy_x
                dy = self.player_y * CELL_SIZE - self.enemy_y
                distance = math.hypot(dx, dy)
                if distance:
                    weight = config.pursuit_weight
                    self.enemy_vx = ((1 - weight) * self.enemy_vx
                                     + weight * dx / distance * config.boss_speed)
                    self.enemy_vy = ((1 - weight) * self.enemy_vy
                                     + weight * dy / distance * config.boss_speed)
            # Normalizza velocità
            speed = math.sqrt(self.enemy_vx**2 + self.enemy_vy**2)
            target_speed = config.boss_speed
            if speed > 0:
                self.enemy_vx = (self.enemy_vx / speed) * target_speed
                self.enemy_vy = (self.enemy_vy / speed) * target_speed

        # 2. Sparo Missili
        shot_interval = self.shock.shot_interval(self.shoot_interval)
        if shot_interval is not None and current_time - self.last_shot_time >= shot_interval:
            self.last_shot_time = current_time
            self._shoot_at_player()

        if not self._update_missiles():
            return

        if not self._move_boss():
            return

        # Input Giocatore
        self._update_player(InputFrame() if keys is None else keys)

    def _shoot_at_player(self):
        """Traiettoria rettilinea verso il player al lancio, in coordinate logiche."""
        dx = self.player_x * CELL_SIZE - self.enemy_x
        dy = self.player_y * CELL_SIZE - self.enemy_y
        distance = math.hypot(dx, dy)
        if distance > 0:
            speed = self.level_config.missile_speed
            self.missiles.append({'x': self.enemy_x, 'y': self.enemy_y,
                                  'vx': dx / distance * speed, 'vy': dy / distance * speed})

    def _update_player(self, keys):
        if self.state != GameState.PLAYING:
            return
        ndx, ndy = keys.direction if isinstance(keys, InputFrame) else keyboard_direction(keys)
        if self._respawn_waiting_for_release:
            # Anche cambiare verso mantenendo una direzione premuta non riavvia
            # il taglio. Il neutro è comune a tastiera, D-pad e stick/deadzone.
            if (ndx, ndy) == (0, 0):
                self._respawn_waiting_for_release = False
            return
        if (ndx != 0 or ndy != 0) and not (ndx == -self.dx and ndy == -self.dy and self.drawing):
            self.dx, self.dy = ndx, ndy
        if self.dx or self.dy:
            try:
                motion = move_player(self.collision_grid, (self.player_x, self.player_y),
                                     self.player_sprite_size, self.dx, self.dy)
            except ValueError as exc:
                self._halt_physics(exc)
                return
            if motion.blocked:
                self.dx = self.dy = 0
            for new_x, new_y in motion.cells:
                is_safe_zone = self.grid[new_x][new_y] == FILLED
                if self._player_motion_hits_hostile(new_x, new_y, is_safe_zone):
                    self._handle_hostile_contact(center=((new_x + .5) * CELL_SIZE,
                                                         (new_y + .5) * CELL_SIZE))
                    return
                if self.drawing and (new_x, new_y) in self.current_trail[:-1]:
                    self.handle_death(center=((new_x + .5) * CELL_SIZE,
                                              (new_y + .5) * CELL_SIZE))
                    return
                if not self.drawing:
                    if is_safe_zone:
                        self.player_x, self.player_y = new_x, new_y
                        self.last_safe_x, self.last_safe_y = new_x, new_y
                    else:
                        self.drawing = True
                        self.current_trail = [(self.player_x, self.player_y), (new_x, new_y)]
                        self.player_x, self.player_y = new_x, new_y
                else:
                    self.player_x, self.player_y = new_x, new_y
                    self.current_trail.append((new_x, new_y))
                if self.drawing:
                    if self._new_trail_hits_boss() or self._new_trail_hits_missile():
                        self._handle_hostile_contact()
                        return
                    if is_safe_zone:
                        self.fill_area()
                        return
        self._sync_draw_audio()

    def _player_motion_hits_hostile(self, x, y, safe):
        if self.shields.grace_ticks:
            return False
        body = self._player_body()
        dx, dy = (x - self.player_x) * CELL_SIZE, (y - self.player_y) * CELL_SIZE
        if self.drawing or not safe:
            if swept_contact(body, self._boss_body(), dx, dy):
                return True
            for missile in tuple(self.missiles):
                if swept_contact(body, self._missile_body(missile), dx, dy):
                    self.missiles.remove(missile)
                    return True
        else:
            return any(swept_contact(body, threat.body, dx, dy) for threat in self.perimeter_threats)
        return False

    def draw(self):
        screen = self.screen
        font = self.font
        # 1. Canvas: copertura SVG nelle celle libere, immagine primaria nelle conquistate.
        canvas = self._capture_canvas if self._capture_canvas is not None else self.canvas
        screen.blit(canvas, (0, 0))

        # 2. Disegna la scia corrente (mentre disegni)
        trail_color = COLOR_TRAIL
        if self.state == GameState.CAPTURING:
            # Feedback solo visivo durante la chiusura; non consuma tick o RNG.
            pulse = (1 + math.sin(pygame.time.get_ticks() * 0.008)) / 2
            trail_color = (255, round(50 + 100 * pulse), 255)
        for (tx, ty) in self.current_trail:
            r = pygame.Rect(tx*CELL_SIZE, ty*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, trail_color, r)

        # 3. Disegna Giocatore
        px, py = self.player_x * CELL_SIZE, self.player_y * CELL_SIZE
        show_death = (self.state == GameState.DYING
                      or self.state == GameState.PAUSED and self._resume_state == GameState.DYING)
        
        if not show_death:
            if self.cursor_img:
                screen.blit(self.cursor_img, self.cursor_img.get_rect(
                    center=(px + CELL_SIZE // 2, py + CELL_SIZE // 2)))
            else:
                bounds = pygame.Rect((0, 0), self.player_sprite_size)
                bounds.center = (px + CELL_SIZE // 2, py + CELL_SIZE // 2)
                pygame.draw.rect(screen, COLOR_PLAYER, bounds)

        if not show_death and (self.shields.active or self.shields.grace_ticks):
            shield = MANIFEST['shields']
            radius = math.ceil(math.hypot(*self.player_sprite_size) / 2) + shield['ring_padding']
            pygame.draw.circle(screen, shield['ring_color'],
                               (px + CELL_SIZE // 2, py + CELL_SIZE // 2), radius, shield['ring_width'])

        # 4. Disegna Nemico
        if self.boss_img:
            boss_rect = self.boss_img.get_rect(
                center=(round(self.enemy_x), round(self.enemy_y)))
            screen.blit(self.boss_img, boss_rect)
        else:
            bounds = pygame.Rect((0, 0), self.boss_size)
            bounds.center = (round(self.enemy_x), round(self.enemy_y))
            pygame.draw.ellipse(screen, COLOR_ENEMY, bounds)

        # 5. Disegna Missili
        for m in self.missiles:
            self.missile_visual.draw(screen, (m['x'], m['y']), (m['vx'], m['vy']))

        for threat in self.perimeter_threats:
            self.threat_visual.draw(screen, threat.position, threat.velocity)

        if show_death and self.death_sequence.center is not None:
            sequence = self.death_sequence
            center = tuple(round(value) for value in sequence.center)
            frame = self.death_frames[sequence.frame_index]
            if frame is not None:
                screen.blit(frame, frame.get_rect(center=center))
            else:
                # Mantiene durata e centro anche con un asset illeggibile.
                radius = round(max(self.player_sprite_size) / 2) + sequence.frame_index
                pygame.draw.circle(screen, MANIFEST['colors']['accent'], center, radius, 2)

        if self.shock.warning and self.state in (GameState.PLAYING, GameState.CAPTURING):
            color = (255, 80, 80) if self.shock.active else (255, 195, 70)
            if self.shock.active:
                message = STRINGS['shock_active']
            else:
                seconds = (self.shock.config.activation_ms - self.shock.elapsed_ms + 999) // 1000
                message = STRINGS['shock_warning'].format(seconds=seconds)
            label = font.render(message, True, color)
            bounds = label.get_rect(center=(WIDTH // 2, 18))
            pygame.draw.rect(screen, (12, 12, 18), bounds.inflate(12, 8))
            screen.blit(label, bounds)

        if self.win:
            screen.blit(self.hidden_image, (0,0))

        if self.physics_error:
            pygame.draw.rect(screen, (0, 0, 0), (20, HEIGHT // 2 - 35, WIDTH - 40, 70))
            screen.blit(font.render(STRINGS['physics_title'], True,
                                    (255, 160, 80)), (30, HEIGHT // 2 - 25))
            screen.blit(font.render(tr('physics_details'), True, (255, 255, 255)),
                        (30, HEIGHT // 2 + 5))

        if self.state == GameState.PAUSED:
            label = font.render(STRINGS['pause'], True, (255, 255, 255))
            bounds = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            pygame.draw.rect(screen, (0, 0, 0), bounds.inflate(24, 20))
            screen.blit(label, bounds)

        if self.state == GameState.PLAYING and self._respawn_waiting_for_release:
            label = font.render(tr('respawn_release'), True, MANIFEST['colors']['text'])
            bounds = label.get_rect(center=(WIDTH // 2, HEIGHT - 32))
            pygame.draw.rect(screen, MANIFEST['colors']['menu_background'], bounds.inflate(16, 10))
            screen.blit(label, bounds)

        if self.shields.notice_ticks and self.state == GameState.PLAYING:
            self.draw_shield_notice()

    def draw_shield_notice(self):
        panel = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 100, 560, 170)
        pygame.draw.rect(self.screen, MANIFEST['colors']['menu_background'], panel, border_radius=12)
        if self.shield_notice_img is not None:
            self.screen.blit(self.shield_notice_img,
                             self.shield_notice_img.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
        for key, y in (('shield_gained', HEIGHT // 2 + 12), ('shield_help', HEIGHT // 2 + 38)):
            label = self.font.render(tr(key), True, MANIFEST['shields']['ring_color'])
            self.screen.blit(label, label.get_rect(center=(WIDTH // 2, y)))

    def dismiss_level_rewards(self):
        self.level_rewards_pending = False
        self.shields.notice_ticks = 0

    def draw_level_rewards(self):
        """Visualizza vita sopra e scudo sotto senza mutare premi o inventario."""
        result = self.level_result
        items = []
        if result.extra_life:
            items.append((self.life_notice_img, tr('reward_life')))
        if result.shields_earned:
            items.append((self.shield_notice_img, tr('reward_shields', count=result.shields_earned)))
        height = 300 if len(items) == 2 else 180
        panel = pygame.Rect(0, 0, 580, height)
        panel.center = WIDTH // 2, HEIGHT // 2
        pygame.draw.rect(self.screen, MANIFEST['colors']['menu_background'], panel, border_radius=12)
        for index, (sprite, message) in enumerate(items):
            y = HEIGHT // 2 - 70 + index * 140 if len(items) == 2 else HEIGHT // 2 - 20
            if sprite is not None:
                self.screen.blit(sprite, sprite.get_rect(center=(WIDTH // 2, y)))
            label = self.font.render(message, True, MANIFEST['colors']['accent'])
            self.screen.blit(label, label.get_rect(center=(WIDTH // 2, y + 47)))

    def hud_data(self):
        hint = tr(self.level_config.hint)
        if self.state == GameState.CAPTURING:
            hint = STRINGS['capture']
        return HudData(self.level, self.lives, self.percent, self.level_config.victory_percent,
                       self.run_score, self.game_clock.elapsed_ms // 1000, hint,
                       self.level_score.bonus(self.game_clock.elapsed_ms), self.shields.charges, self.cycle)

def main():
    from application import CampaignApp
    audio = MANIFEST['audio']
    pygame.mixer.pre_init(audio['sample_rate'], audio['sample_bits'], audio['channels'], audio['buffer_size'])
    pygame.init()
    window = pygame.display.set_mode(VIEWPORT_SIZE)
    hud = Hud(*VIEWPORT_SIZE)
    viewport = Viewport(window, (WIDTH, HEIGHT), area=hud.game_area)
    pygame.display.set_caption(MANIFEST['title'])
    clock = pygame.time.Clock()
    app = None
    try:
        app = CampaignApp(viewport.surface, Game)
        while app.running:
            for event in pygame.event.get():
                app.handle_event(event)
            if not app.running:
                break
            app.advance()
            app.draw()
            viewport.present(lambda target: hud.draw(target, app.hud_data()))
            clock.tick(RENDER_FPS_LIMIT)
    finally:
        if app is not None:
            app.close()
        pygame.quit()

if __name__ == "__main__":
    main()
