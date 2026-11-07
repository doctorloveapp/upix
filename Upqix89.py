import pygame
import collections
import math
import random
from pathlib import Path

# --- CONFIGURAZIONE ---
WIDTH, HEIGHT = 800, 600
CELL_SIZE = 2  # Alta risoluzione
COLS = WIDTH // CELL_SIZE
ROWS = HEIGHT // CELL_SIZE
ASSET_DIR = Path(__file__).resolve().parent / "public"
MUSIC_VOLUME = 0.26
DRAW_MUSIC_VOLUME = 0.10
DRAW_VOLUME = 0.80
BOSS_SPRITE_FILENAME = "boss2.png"
BOSS_SPRITE_MAX_SIZE = (40, 40)
BOSS_COLLISION_RADIUS = 15

# Colori
COLOR_BG_COVER = (0, 0, 0)       # Il colore che "copre" l'immagine (Nero)
COLOR_PLAYER = (255, 255, 0)     # Giallo
COLOR_TRAIL = (255, 50, 255)     # Magenta
COLOR_ENEMY = (255, 0, 0)        # Rosso

# Stati
EMPTY = 0
FILLED = 1

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("monospace", 16, bold=True)
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

        width, height = image.get_size()
        max_width, max_height = BOSS_SPRITE_MAX_SIZE
        scale = min(max_width / width, max_height / height)
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        # Nearest-neighbor mantiene i contorni della pixel art e il canale alpha.
        return pygame.transform.scale(image, size)

    def handle_death(self):
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
            self.game_over = True

    def _stop_draw_audio(self):
        if self.draw_channel is not None:
            self.draw_channel.stop()
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(MUSIC_VOLUME)

    def _sync_draw_audio(self):
        """La saldatrice segue il tracciamento, mai lo spostamento in zona sicura."""
        active = (self.drawing and not self.game_over and not self.win
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
        self._stop_draw_audio()
        self.grid = [[EMPTY for _ in range(ROWS)] for _ in range(COLS)]
        
        # --- CARICAMENTO IMMAGINE LIVELLO ---
        # Format 01.png, 02.png ...
        img_name = f"{self.level:02d}.png"
        image_path = ASSET_DIR / "assets" / img_name
        
        print(f"Caricamento livello {self.level}: {image_path}")

        # Se l'immagine non esiste, crea un gradiente colorato di fallback
        if image_path.exists():
            try:
                self.hidden_image = pygame.image.load(image_path).convert()
                self.hidden_image = pygame.transform.scale(self.hidden_image, (WIDTH, HEIGHT))
            except (pygame.error, OSError) as exc:
                print(f"Errore caricamento immagine: {exc}. Uso fallback.")
                self.hidden_image = self._create_fallback_image()
        else:
            print(f"Immagine non trovata in {image_path}. Uso fallback.")
            self.hidden_image = self._create_fallback_image()

        # --- SURFACE DI GIOCO (CANVAS) ---
        # Questa è la superficie che vediamo. Inizia tutta nera (o colore cover).
        # Man mano che vinciamo, ci "incolliamo" sopra pezzi di hidden_image.
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.canvas.fill(COLOR_BG_COVER)

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
        
        # La fisica resta identica anche se lo sprite non è disponibile.
        self.enemy_radius = BOSS_COLLISION_RADIUS
        
        # Boss Behavior
        self.missiles = []
        self.last_shot_time = pygame.time.get_ticks()
        self.enemy_change_dir_timer = pygame.time.get_ticks()
        self.shoot_interval = max(500, 2000 - (self.level * 100)) # Spara più spesso ai livelli alti

        self.game_over = False
        self.win = False
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
        self._stop_draw_audio()

        # 1. Converti la scia corrente in area riempita
        for (tx, ty) in self.current_trail:
            self.grid[tx][ty] = FILLED
            self._reveal_pixel(tx, ty) # Svela l'immagine sotto la scia

        # 2. Flood Fill per trovare DOVE STA il nemico
        ex_grid = int(self.enemy_x // CELL_SIZE)
        ey_grid = int(self.enemy_y // CELL_SIZE)
        
        ex_grid = max(0, min(ex_grid, COLS-1))
        ey_grid = max(0, min(ey_grid, ROWS-1))

        visited = set()
        queue = collections.deque([(ex_grid, ey_grid)])
        visited.add((ex_grid, ey_grid))
        
        while queue:
            cx, cy = queue.popleft()
            neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
            for nx, ny in neighbors:
                if 0 <= nx < COLS and 0 <= ny < ROWS:
                    if self.grid[nx][ny] != FILLED and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))

        # 3. Tutto ciò che NON è stato visitato (e non è già pieno) è stato CATTURATO
        filled_count_this_turn = 0
        
        # Ottimizzazione: Scorriamo la griglia. 
        # Se un punto è vuoto e non è stato raggiunto dal nemico, lo riempiamo.
        for x in range(COLS):
            for y in range(ROWS):
                if self.grid[x][y] == EMPTY and (x, y) not in visited:
                    self.grid[x][y] = FILLED
                    self._reveal_pixel(x, y) # <--- MAGIA: Qui sveliamo l'immagine
                    filled_count_this_turn += 1
        
        self.score += filled_count_this_turn * 10
        
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
            self.win = True

    def update(self):
        if self.game_over or self.win:
            self._stop_draw_audio()
            return

        current_time = pygame.time.get_ticks()

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

        # 3. Aggiorna Missili
        for m in self.missiles[:]:
            m['x'] += m['vx']
            m['y'] += m['vy']
            
            # Rimuovi se fuori schermo
            if not (0 <= m['x'] <= WIDTH and 0 <= m['y'] <= HEIGHT):
                self.missiles.remove(m)
                continue
                
            # Collisione Missile -> Aree Piene (Scudo)
            mx_g = int(m['x'] // CELL_SIZE)
            my_g = int(m['y'] // CELL_SIZE)
            if 0 <= mx_g < COLS and 0 <= my_g < ROWS:
                if self.grid[mx_g][my_g] == FILLED:
                    self.missiles.remove(m)
                    continue
            
            # Collisione Missile -> Player
            m_rect = pygame.Rect(m['x']-2, m['y']-2, 4, 4)
            p_rect = self.get_pixel_rect(self.player_x, self.player_y)
            if m_rect.colliderect(p_rect):
                if self.drawing:
                    self.handle_death()
                    return
            
            # Collisione Missile -> Scia
            for (tx, ty) in self.current_trail:
                t_rect = self.get_pixel_rect(tx, ty)
                if m_rect.colliderect(t_rect):
                    self.handle_death()
                    return

        # Movimento Nemico
        self.enemy_x += self.enemy_vx
        self.enemy_y += self.enemy_vy

        # Rimbalzi bordi schermo
        if self.enemy_x <= self.enemy_radius or self.enemy_x >= WIDTH - self.enemy_radius: 
            self.enemy_vx *= -1
        if self.enemy_y <= self.enemy_radius or self.enemy_y >= HEIGHT - self.enemy_radius: 
            self.enemy_vy *= -1

        # Rimbalzi su Aree Piene (Svelate)
        ex_g = int(self.enemy_x // CELL_SIZE)
        ey_g = int(self.enemy_y // CELL_SIZE)
        
        # Controllo collisione semplificato al centro del nemico
        if 0 <= ex_g < COLS and 0 <= ey_g < ROWS:
            if self.grid[ex_g][ey_g] == FILLED:
                self.enemy_vx *= -1
                self.enemy_vy *= -1
                self.enemy_x += self.enemy_vx * 2
                self.enemy_y += self.enemy_vy * 2

        # Collisione Nemico -> Scia
        enemy_rect = pygame.Rect(self.enemy_x - self.enemy_radius, self.enemy_y - self.enemy_radius,
                                 self.enemy_radius*2, self.enemy_radius*2)

        for (tx, ty) in self.current_trail:
            trail_rect = self.get_pixel_rect(tx, ty)
            if trail_rect.colliderect(enemy_rect):
                self.handle_death()
                return

        # Collisione Nemico -> Giocatore
        player_rect = self.get_pixel_rect(self.player_x, self.player_y)
        if player_rect.inflate(4,4).colliderect(enemy_rect):
            if self.drawing:
                self.handle_death()
                return

        # Input Giocatore
        self._update_player(pygame.key.get_pressed())

    def _update_player(self, keys):
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
            else:
                if (new_x, new_y) in self.current_trail[:-1]:
                    self.handle_death() # Snake death
                    return
                
                self.player_x, self.player_y = new_x, new_y
                self.current_trail.append((new_x, new_y))

                if is_safe_zone:
                    self.fill_area()

        self._sync_draw_audio()

    def draw(self):
        screen = self.screen
        font = self.font
        # 1. Disegna il Canvas (che contiene l'immagine svelata e lo sfondo nero)
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
            pygame.draw.circle(screen, COLOR_ENEMY,
                               (round(self.enemy_x), round(self.enemy_y)), self.enemy_radius)

        # 5. Disegna Missili
        for m in self.missiles:
            pygame.draw.circle(screen, (255, 100, 100), (int(m['x']), int(m['y'])), 3)

        # UI
        text = font.render(f"LVL {self.level} | LIVES: {self.lives} | CLEARED: {self.percent:.1f}%", True, (255, 255, 255))
        pygame.draw.rect(screen, (0,0,0), (5, 5, 350, 30)) # Sfondo testo leggibile
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
                if event.type == pygame.KEYDOWN:
                    if game.game_over and event.key == pygame.K_r:
                        game._stop_draw_audio()
                        game = Game(screen)
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
