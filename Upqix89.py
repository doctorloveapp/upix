import pygame
import math
import random
from pathlib import Path
from assets import load_level_cover, load_level_image
from collisions import AABB, CollisionGrid, move_body, move_projectile
from game_state import GameState, SimulationClock
from territory import CaptureContactError, plan_capture

# --- CONFIGURAZIONE ---
WIDTH, HEIGHT = 800, 600
CELL_SIZE = 2  # Alta risoluzione
COLS = WIDTH // CELL_SIZE
ROWS = HEIGHT // CELL_SIZE
ASSET_DIR = Path(__file__).resolve().parent / "public"
MUSIC_VOLUME = 0.26
DRAW_MUSIC_ATTENUATION = 0.105  # Riduzione dimezzata rispetto alla precedente (0.21).
DRAW_MUSIC_VOLUME = MUSIC_VOLUME - DRAW_MUSIC_ATTENUATION
DRAW_VOLUME = 0.80
BOSS_SPRITE_FILENAME = "boss2.png"
BOSS_SIZE = (96, 70)  # Unico parametro per sprite e hitbox, come richiesto.
MISSILE_COLLISION_SIZE = 4
MISSILE_RENDER_RADIUS = 3

# Colori
COLOR_BG_COVER = (0, 0, 0)       # Copertura di emergenza se manca l'SVG.
COLOR_PLAYER = (255, 255, 0)     # Giallo
COLOR_TRAIL = (255, 50, 255)     # Magenta
COLOR_ENEMY = (255, 0, 0)        # Rosso

# Stati
EMPTY = 0
FILLED = 1

class Game:
    def __init__(self, screen, *, time_source=None):
        self.screen = screen
        self.font = pygame.font.SysFont("monospace", 16, bold=True)
        self.state = GameState.PLAYING
        self.game_clock = SimulationClock(time_source)
        # --- AUDIO SETUP ---
        self.sound_draw = None
        self.draw_channel = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            # Il canale 0 appartiene alla saldatrice, anche con altri effetti futuri.
            pygame.mixer.set_reserved(1)
            self.draw_channel = pygame.mixer.Channel(0)
            self.draw_channel.stop()
            # WAV pronto per effetti brevi; l'MP3 originale resta un fallback.
            for filename in ("saldatrice.wav", "saldatrice.mp3"):
                sound_path = ASSET_DIR / "sounds" / filename
                try:
                    self.sound_draw = pygame.mixer.Sound(str(sound_path))
                    self.sound_draw.set_volume(DRAW_VOLUME)
                    break
                except (pygame.error, OSError) as exc:
                    print(f"Effetto audio non disponibile ({sound_path}): {exc}")
        except pygame.error as exc:
            print(f"Audio disabilitato: {exc}")

        # Carica Cursore
        cursor_path = ASSET_DIR / "icon" / "cursor_lukso.png"
        if cursor_path.exists():
            self.cursor_img = pygame.image.load(cursor_path).convert_alpha()
            # Ridimensiona il cursore per adattarlo alla cella (un po' più grande per visibilità)
            # Manteniamo la dimensione visiva come se la cella fosse 5px (5*3 = 15px)
            target_size = 15
            self.cursor_img = pygame.transform.scale(self.cursor_img, (target_size, target_size))
        else:
            self.cursor_img = None
            print("Cursore non trovato")

        self.boss_img = self._load_boss_sprite()

        # Playlist Musicale
        self.music_tracks = ["01pink.mp3", "02gold.mp3", "03silver.mp3", "04black.mp3"]
        self.current_music_idx = 0
        self._play_music()

        # Livelli
        self.level = 1
        self.max_levels = 12
        self.lives = 3
        
        self.start_level()

    def _load_boss_sprite(self):
        """Carica lo sprite RGBA senza alterare proporzioni o geometria fisica."""
        boss_path = ASSET_DIR / "icon" / BOSS_SPRITE_FILENAME
        try:
            image = pygame.image.load(str(boss_path)).convert_alpha()
        except (pygame.error, OSError) as exc:
            print(f"Sprite boss non disponibile ({boss_path}): {exc}")
            return None

        # Nearest-neighbor mantiene i contorni della pixel art e il canale alpha.
        return pygame.transform.scale(image, BOSS_SIZE)

    @property
    def game_over(self):
        return self.state == GameState.GAME_OVER

    @property
    def win(self):
        return self.state == GameState.LEVEL_CLEAR

    def _set_state(self, state: GameState):
        if self.state == state:
            return
        previous = self.state
        self.state = state
        if state == GameState.PLAYING:
            self.game_clock.resume()
            if previous == GameState.PAUSED:
                self._resume_audio()
            self._sync_draw_audio()
        else:
            self.game_clock.pause()
            if state == GameState.PAUSED:
                if pygame.mixer.get_init():
                    pygame.mixer.pause()
                    pygame.mixer.music.pause()
            else:
                if previous == GameState.PAUSED:
                    self._resume_audio()
                self._stop_draw_audio()

    def _resume_audio(self):
        if pygame.mixer.get_init():
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()

    def pause(self):
        if self.state == GameState.PLAYING:
            self._set_state(GameState.PAUSED)

    def toggle_pause(self):
        if self.state == GameState.PAUSED:
            self._set_state(GameState.PLAYING)
        else:
            self.pause()

    def handle_death(self):
        if self.state != GameState.PLAYING:
            return
        self.lives -= 1
        self._stop_draw_audio()
        self.dx = self.dy = 0
        self.drawing = False
        self.current_trail = []
        self.missiles = []
        
        if self.lives > 0:
            print(f"Vite rimaste: {self.lives}")
            # Respawn all'ultima posizione sicura conosciuta
            self.player_x = self.last_safe_x
            self.player_y = self.last_safe_y
            
        else:
            self._set_state(GameState.GAME_OVER)

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
        if not pygame.mixer.get_init():
            return
        pygame.mixer.music.stop()
        track_name = self.music_tracks[self.current_music_idx % len(self.music_tracks)]
        music_path = ASSET_DIR / "music" / track_name
        try:
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(-1) # Loop infinito
        except (pygame.error, OSError) as exc:
            print(f"Musica non disponibile ({music_path}): {exc}")

    def start_level(self):
        if self.state == GameState.PAUSED:
            self._resume_audio()
        self._stop_draw_audio()
        self.physics_error = None
        self.grid = [[EMPTY for _ in range(ROWS)] for _ in range(COLS)]
        self.collision_grid = CollisionGrid(self.grid, CELL_SIZE, FILLED)
        
        # --- CARICAMENTO IMMAGINE LIVELLO ---
        # Format 01.png, 02.png ...
        self.hidden_image, self.primary_image_source = load_level_image(
            ASSET_DIR, self.level, (WIDTH, HEIGHT))
        if self.hidden_image is None:
            self.hidden_image = self._create_fallback_image()

        # --- SURFACE DI GIOCO (CANVAS) ---
        # L'SVG copre il campo; la conquista lo sostituisce con l'immagine primaria.
        self.canvas, self.cover_source = load_level_cover(ASSET_DIR, self.level, (WIDTH, HEIGHT))
        if self.canvas is None:
            self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
            self.canvas.fill(COLOR_BG_COVER)
        print(f"Livello {self.level}: immagine={self.primary_image_source or 'procedurale'}, "
              f"copertura={self.cover_source or 'neutra'}")

        # Setup bordi iniziali (sveliamo i bordi dell'immagine)
        border_thick = 2
        for x in range(COLS):
            for y in range(ROWS):
                # Se è un bordo
                if x < border_thick or x >= COLS - border_thick or y < border_thick or y >= ROWS - border_thick:
                    self.grid[x][y] = FILLED
                    # Sveliamo il pixel sul canvas
                    self._reveal_pixel(x, y)

        self.player_x = COLS // 2
        self.player_y = ROWS - border_thick
        self.last_safe_x = self.player_x
        self.last_safe_y = self.player_y
        
        self.dx = 0
        self.dy = 0
        self.drawing = False
        self.current_trail = [] 
        
        self.enemy_x = WIDTH // 2
        self.enemy_y = HEIGHT // 2
        # Aumenta leggermente la velocità ogni livello
        speed_mult = 1.0 + (self.level * 0.1)
        self.enemy_vx = 3.0 * speed_mult
        self.enemy_vy = 3.0 * speed_mult
        
        # Boss Behavior
        self.missiles = []
        self.game_clock.reset()
        self.last_shot_time = 0
        self.enemy_change_dir_timer = 0
        self.shoot_interval = max(500, 2000 - (self.level * 100)) # Spara più spesso ai livelli alti

        self.state = GameState.PLAYING
        self.score = 0
        self.percent = 0.0

    def next_level(self):
        if self.level < self.max_levels:
            self.level += 1
            self.current_music_idx += 1
            self._play_music()
            self.start_level()
        else:
            # Ricomincia o fine gioco? Per ora loop
            self.level = 1
            self.current_music_idx = 0
            self._play_music()
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
        try:
            capture = plan_capture(self.collision_grid, self.current_trail, self._boss_body())
        except CaptureContactError:
            self.handle_death()
            return
        except ValueError as exc:
            self._halt_physics(exc)
            return
        # Tutti i vincoli sono verificati prima di modificare griglia e canvas.
        for x, y in capture.cells:
            self.grid[x][y] = FILLED
            self._reveal_pixel(x, y)
        self.score += capture.area_count * 10
        
        # Reset Player
        self.current_trail = []
        self.drawing = False
        self.dx, self.dy = 0, 0
        self.last_safe_x, self.last_safe_y = self.player_x, self.player_y
        
        # Calcolo Percentuale
        total_cells = COLS * ROWS
        # Conta celle piene
        # (Nota: per performance potremmo tenere un contatore incrementale invece di ricalcolare tutto)
        total_filled = sum(row.count(FILLED) for row in self.grid)
        self.percent = (total_filled / total_cells) * 100

        if self.percent >= 80.0: # Vinci all'80%
            self._set_state(GameState.LEVEL_CLEAR)

    def _boss_body(self):
        return AABB.from_center(self.enemy_x, self.enemy_y, *BOSS_SIZE)

    def _halt_physics(self, error):
        self.physics_error = str(error)
        self.dx = self.dy = 0
        self._set_state(GameState.PHYSICS_ERROR)
        print(f"Simulazione sospesa: {self.physics_error}")

    def _move_boss(self):
        trail = frozenset((x, y) for x, y in self.current_trail if self.grid[x][y] == EMPTY)
        player = None
        if self.drawing and self.grid[self.player_x][self.player_y] == EMPTY:
            px, py = self.player_x * CELL_SIZE, self.player_y * CELL_SIZE
            player = AABB(px - 2, py - 2, px + CELL_SIZE + 2, py + CELL_SIZE + 2)
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
            self.handle_death()
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

    def _update_missiles(self):
        trail = frozenset((x, y) for x, y in self.current_trail if self.grid[x][y] == EMPTY)
        player = None
        if self.drawing and self.grid[self.player_x][self.player_y] == EMPTY:
            px, py = self.player_x * CELL_SIZE, self.player_y * CELL_SIZE
            player = AABB(px, py, px + CELL_SIZE, py + CELL_SIZE)
        survivors = []
        try:
            for missile in self.missiles:
                result = move_projectile(self.collision_grid, self._missile_body(missile),
                                         missile['vx'], missile['vy'], trail=trail, player=player)
                if result.hit == "wall":
                    continue
                if result.hit is not None:
                    self.handle_death()
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

    def update(self):
        if self.state != GameState.PLAYING:
            return

        current_time = self.game_clock.elapsed_ms

        # --- BOSS AI ---
        # 1. Movimento Randomico
        if current_time - self.enemy_change_dir_timer > 1000: # Ogni secondo cambia un po' direzione
            self.enemy_change_dir_timer = current_time
            # Aggiunge componente casuale
            self.enemy_vx += random.uniform(-2.0, 2.0)
            self.enemy_vy += random.uniform(-2.0, 2.0)
            # Normalizza velocità
            speed = math.sqrt(self.enemy_vx**2 + self.enemy_vy**2)
            target_speed = 3.0 * (1.0 + (self.level * 0.1))
            if speed > 0:
                self.enemy_vx = (self.enemy_vx / speed) * target_speed
                self.enemy_vy = (self.enemy_vy / speed) * target_speed

        # 2. Sparo Missili
        if current_time - self.last_shot_time > self.shoot_interval:
            self.last_shot_time = current_time
            # Calcola direzione verso il player
            dx = (self.player_x * CELL_SIZE) - self.enemy_x
            dy = (self.player_y * CELL_SIZE) - self.enemy_y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                mvx = (dx / dist) * 5.0
                mvy = (dy / dist) * 5.0
                self.missiles.append({'x': self.enemy_x, 'y': self.enemy_y, 'vx': mvx, 'vy': mvy})

        if not self._update_missiles():
            return

        if not self._move_boss():
            return

        # Input Giocatore
        self._update_player(pygame.key.get_pressed())

    def _update_player(self, keys):
        if self.state != GameState.PLAYING:
            return
        ndx, ndy = 0, 0
        if keys[pygame.K_UP]: ndy = -1
        elif keys[pygame.K_DOWN]: ndy = 1
        elif keys[pygame.K_LEFT]: ndx = -1
        elif keys[pygame.K_RIGHT]: ndx = 1

        if (ndx != 0 or ndy != 0) and not (ndx == -self.dx and ndy == -self.dy and self.drawing):
            self.dx, self.dy = ndx, ndy

        if self.dx != 0 or self.dy != 0:
            new_x = self.player_x + self.dx
            new_y = self.player_y + self.dy
            new_x = max(0, min(new_x, COLS - 1))
            new_y = max(0, min(new_y, ROWS - 1))

            is_safe_zone = (self.grid[new_x][new_y] == FILLED)
            
            if not self.drawing:
                if is_safe_zone:
                    self.player_x, self.player_y = new_x, new_y
                    self.last_safe_x = self.player_x
                    self.last_safe_y = self.player_y
                else:
                    self.drawing = True
                    self.current_trail.append((self.player_x, self.player_y))
                    self.player_x, self.player_y = new_x, new_y
                    self.current_trail.append((new_x, new_y))
                    if self._new_trail_hits_boss() or self._new_trail_hits_missile():
                        self.handle_death()
                        return
            else:
                if (new_x, new_y) in self.current_trail[:-1]:
                    self.handle_death() # Snake death
                    return
                
                self.player_x, self.player_y = new_x, new_y
                self.current_trail.append((new_x, new_y))

                if self._new_trail_hits_boss() or self._new_trail_hits_missile():
                    self.handle_death()
                    return

                if is_safe_zone:
                    self.fill_area()

        self._sync_draw_audio()

    def draw(self):
        screen = self.screen
        font = self.font
        # 1. Canvas: copertura SVG nelle celle libere, immagine primaria nelle conquistate.
        screen.blit(self.canvas, (0, 0))

        # 2. Disegna la scia corrente (mentre disegni)
        for (tx, ty) in self.current_trail:
            r = pygame.Rect(tx*CELL_SIZE, ty*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, COLOR_TRAIL, r)

        # 3. Disegna Giocatore
        px, py = self.player_x * CELL_SIZE, self.player_y * CELL_SIZE
        
        if self.cursor_img:
            # Centra l'immagine del cursore sulla posizione del giocatore
            # Offset per centrare l'immagine
            offset = (self.cursor_img.get_width() - CELL_SIZE) // 2
            screen.blit(self.cursor_img, (px - offset, py - offset))
        else:
            pygame.draw.rect(screen, COLOR_PLAYER, (px, py, CELL_SIZE, CELL_SIZE))

        # 4. Disegna Nemico
        if self.boss_img:
            boss_rect = self.boss_img.get_rect(
                center=(round(self.enemy_x), round(self.enemy_y)))
            screen.blit(self.boss_img, boss_rect)
        else:
            bounds = pygame.Rect((0, 0), BOSS_SIZE)
            bounds.center = (round(self.enemy_x), round(self.enemy_y))
            pygame.draw.ellipse(screen, COLOR_ENEMY, bounds)

        # 5. Disegna Missili
        for m in self.missiles:
            pygame.draw.circle(screen, (255, 100, 100), (round(m['x']), round(m['y'])),
                               MISSILE_RENDER_RADIUS)

        # UI
        seconds = self.game_clock.elapsed_ms // 1000
        hud = (f"LVL {self.level} | LIVES: {self.lives} | CLEARED: {self.percent:.1f}%"
               f" | TIME: {seconds // 60:02d}:{seconds % 60:02d}")
        text = font.render(hud, True, (255, 255, 255))
        pygame.draw.rect(screen, (0,0,0), (5, 5, text.get_width() + 10, 30))
        screen.blit(text, (10, 10))

        if self.game_over:
            txt = font.render("GAME OVER - Premi R", True, (255, 0, 0))
            screen.blit(txt, (WIDTH//2 - 80, HEIGHT//2))
        
        if self.win:
            # Se vinci, mostriamo tutta l'immagine
            screen.blit(self.hidden_image, (0,0))
            txt = font.render("STAGE CLEAR! - Premi SPAZIO", True, (0, 255, 0))
            pygame.draw.rect(screen, (0,0,0), (WIDTH//2 - 120, HEIGHT//2, 260, 30))
            screen.blit(txt, (WIDTH//2 - 110, HEIGHT//2 + 5))

        if self.physics_error:
            pygame.draw.rect(screen, (0, 0, 0), (20, HEIGHT // 2 - 35, WIDTH - 40, 70))
            screen.blit(font.render("FISICA SOSPESA - Premi R per ripartire dal livello", True,
                                    (255, 160, 80)), (30, HEIGHT // 2 - 25))
            screen.blit(font.render(self.physics_error, True, (255, 255, 255)),
                        (30, HEIGHT // 2 + 5))

        if self.state == GameState.PAUSED:
            label = font.render("PAUSA - Premi P per riprendere", True, (255, 255, 255))
            bounds = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            pygame.draw.rect(screen, (0, 0, 0), bounds.inflate(24, 20))
            screen.blit(label, bounds)

        pygame.display.flip()

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("UPIX 1989 - Reveal The Image")
    clock = pygame.time.Clock()
    game = None
    try:
        game = Game(screen)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.WINDOWFOCUSLOST:
                    game.pause()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        game.toggle_pause()
                    if game.game_over and event.key == pygame.K_r:
                        game._stop_draw_audio()
                        game = Game(screen)
                    elif game.physics_error and event.key == pygame.K_r:
                        game.start_level()
                    if game.win and event.key == pygame.K_SPACE:
                        game.next_level()
                    if event.key == pygame.K_q:
                        running = False
            if not running:
                break
            game.update()
            game.draw()
            clock.tick(60)
    finally:
        if game is not None:
            game._stop_draw_audio()
        pygame.quit()

if __name__ == "__main__":
    main()
