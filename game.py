# =============================================================================
#  game.py  --  "Colour Swap", a little puzzle platformer
# =============================================================================
#
#  HOW TO RUN THIS GAME:
#     1. Install Pygame (only needed once):   pip install pygame
#     2. Start the game:                       python game.py
#
#  The world has two colours: BLUE and PINK. Press SHIFT to swap which one is
#  "active". Blue platforms are solid only in BLUE mode, pink platforms only
#  in PINK mode. Jump, swap in mid-air, and land on a platform that just
#  appeared. That's the whole game!
#
#  All the levels live in the other file, "levels.py". You can edit those
#  without touching this file at all.
# =============================================================================

import asyncio                       # lets the game run inside a web browser
import pygame
from levels import LEVELS


# =============================================================================
#  SETTINGS  --  CHANGE THESE NUMBERS TO CHANGE THE GAME!
#  Every value here is "wired up", so tweaking one really changes how it plays.
# =============================================================================

PLAYER_NAME   = "Star"             # the hero's name, shown on the title screen
PLAYER_COLOUR = (255, 220, 0)      # the hero's colour (Red, Green, Blue 0-255)
PLAYER_SPEED  = 5                  # how fast she runs (pixels each frame)
JUMP_STRENGTH = 13                 # how high she jumps (bigger = higher)
GRAVITY       = 0.6                # how fast she falls (bigger = heavier)
COYOTE_TIME   = 0.1                # seconds you can still jump after a ledge
JUMP_BUFFER   = 0.1                # seconds early a jump press still "counts"
SWAP_KEY_HINT = True               # show a "press SHIFT to swap" reminder?
START_COLOUR  = "BLUE"             # which colour is active when a level begins

# A few more things you are welcome to play with:
MAX_FALL_SPEED = 15                # the fastest she can fall (stops her zooming)
PLAYER_WIDTH   = 22                # how wide the hero is (pixels)
PLAYER_HEIGHT  = 28                # how tall the hero is (pixels)


# =============================================================================
#  FIXED NUMBERS  --  these describe the screen and grid. Usually leave alone.
# =============================================================================

TILE   = 32                        # each square is 32x32 pixels
GRID_W = 30                        # the level is 30 squares wide
GRID_H = 20                        # the level is 20 squares tall
SCREEN_WIDTH  = GRID_W * TILE      # = 960
SCREEN_HEIGHT = GRID_H * TILE      # = 640
FPS = 60                           # frames per second

# Colours used for drawing (Red, Green, Blue), each 0 to 255.
COL_BLUE       = (60, 140, 255)
COL_PINK       = (255, 100, 180)
COL_GREY       = (120, 120, 135)
COL_SPIKE      = (225, 70, 70)
COL_GOAL       = (90, 220, 130)
COL_GEM        = (255, 235, 90)
COL_CHECKPOINT = (190, 150, 255)
COL_BG_TOP     = (28, 24, 48)      # background colour at the top of the screen
COL_BG_BOTTOM  = (12, 10, 24)      # background colour at the bottom
COL_TEXT       = (240, 240, 255)

# Turn the "seconds" settings into a number of frames (the game thinks in frames)
COYOTE_FRAMES = int(COYOTE_TIME * FPS)
BUFFER_FRAMES = int(JUMP_BUFFER * FPS)


# =============================================================================
#  THE PLAYER
#  A simple class that just remembers where Star is and how she is moving.
# =============================================================================

class Player:
    """Holds the hero's position and speed, nothing fancy."""

    def __init__(self, x, y):
        self.x = float(x)          # left edge, in pixels
        self.y = float(y)          # top edge, in pixels
        self.vx = 0.0              # sideways speed
        self.vy = 0.0              # up/down speed
        self.on_ground = False     # is she standing on something solid?
        self.facing = 1            # 1 = looking right, -1 = looking left

    def rect(self):
        """Give back the rectangle that covers the hero (used for collisions)."""
        return pygame.Rect(int(self.x), int(self.y), PLAYER_WIDTH, PLAYER_HEIGHT)


# =============================================================================
#  LOADING A LEVEL
# =============================================================================

def load_level(index):
    """Read one level from levels.py and turn it into a grid we can edit."""
    rows = LEVELS[index]
    # Make a 2D grid of letters that we are allowed to change while playing.
    tiles = [list(row) for row in rows]

    # Find where the player starts, then erase the '@' so it isn't drawn.
    start_col, start_row = 1, 1
    for row in range(GRID_H):
        for col in range(GRID_W):
            if tiles[row][col] == '@':
                start_col, start_row = col, row
                tiles[row][col] = '.'
    return tiles, start_col, start_row


def tile_to_pixels(col, row):
    """Give back the rectangle for the square at this column and row."""
    return pygame.Rect(col * TILE, row * TILE, TILE, TILE)


def is_solid(letter, active_colour):
    """Say whether a square is solid right now, based on the active colour."""
    if letter == '#':
        return True                              # grey is always solid
    if letter == 'B':
        return active_colour == "BLUE"           # blue only counts in BLUE mode
    if letter == 'P':
        return active_colour == "PINK"           # pink only counts in PINK mode
    return False                                 # everything else you fall through


# =============================================================================
#  MOVING AND BUMPING INTO THINGS
#  We move sideways first and fix overlaps, then up/down and fix overlaps.
#  This keeps the collision code short and easy to follow.
# =============================================================================

def solid_tiles_near(player, tiles, active_colour):
    """Find the solid squares close to the hero (so we don't check all 600)."""
    found = []
    r = player.rect()
    # Look one square past each edge of the hero, just to be safe.
    first_col = max(0, r.left // TILE - 1)
    last_col  = min(GRID_W - 1, r.right // TILE + 1)
    first_row = max(0, r.top // TILE - 1)
    last_row  = min(GRID_H - 1, r.bottom // TILE + 1)
    for row in range(first_row, last_row + 1):
        for col in range(first_col, last_col + 1):
            if is_solid(tiles[row][col], active_colour):
                found.append((col, row))
    return found


def move_horizontal(player, tiles, active_colour):
    """Move the hero left/right, then push her out of any solid square."""
    player.x += player.vx
    r = player.rect()
    for col, row in solid_tiles_near(player, tiles, active_colour):
        block = tile_to_pixels(col, row)
        if r.colliderect(block):
            if player.vx > 0:        # moving right -> stop at the block's left
                r.right = block.left
            elif player.vx < 0:      # moving left -> stop at the block's right
                r.left = block.right
            player.x = float(r.x)
            r = player.rect()


def move_vertical(player, tiles, active_colour):
    """Move the hero up/down, then push her out and notice if she landed."""
    player.y += player.vy
    player.on_ground = False
    r = player.rect()
    for col, row in solid_tiles_near(player, tiles, active_colour):
        block = tile_to_pixels(col, row)
        if r.colliderect(block):
            if player.vy > 0:        # falling -> land on top of the block
                r.bottom = block.top
                player.on_ground = True
                player.vy = 0
            elif player.vy < 0:      # jumping -> bonk your head, start falling
                r.top = block.bottom
                player.vy = 0
            player.y = float(r.y)
            r = player.rect()


# =============================================================================
#  TRIGGERS  --  the squares that DO something when you touch them.
# =============================================================================

def find_touched_tiles(player, tiles, letter):
    """Give back a list of (col, row) for every 'letter' square the hero touches."""
    touched = []
    r = player.rect()
    for row in range(GRID_H):
        for col in range(GRID_W):
            if tiles[row][col] == letter:
                # Make spikes a little smaller so they feel fair to touch.
                pad = 8 if letter == '^' else 0
                box = tile_to_pixels(col, row).inflate(-pad, -pad)
                if r.colliderect(box):
                    touched.append((col, row))
    return touched


# =============================================================================
#  DRAWING
# =============================================================================

def draw_background(screen):
    """Paint a simple top-to-bottom colour fade behind everything."""
    for y in range(0, SCREEN_HEIGHT, 4):
        blend = y / SCREEN_HEIGHT
        colour = (
            int(COL_BG_TOP[0] + (COL_BG_BOTTOM[0] - COL_BG_TOP[0]) * blend),
            int(COL_BG_TOP[1] + (COL_BG_BOTTOM[1] - COL_BG_TOP[1]) * blend),
            int(COL_BG_TOP[2] + (COL_BG_BOTTOM[2] - COL_BG_TOP[2]) * blend),
        )
        pygame.draw.rect(screen, colour, (0, y, SCREEN_WIDTH, 4))


def draw_block(screen, rect, colour, solid):
    """Draw a platform block. If it isn't solid right now, draw it faded."""
    if solid:
        pygame.draw.rect(screen, colour, rect, border_radius=4)
        # a lighter line on top to make it look chunky
        lighter = tuple(min(255, c + 40) for c in colour)
        pygame.draw.rect(screen, lighter, (rect.x, rect.y, rect.width, 5),
                         border_radius=4)
    else:
        # Faded: you can still SEE it so you can plan, but you fall through it.
        ghost = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        faint = (colour[0], colour[1], colour[2], 70)
        pygame.draw.rect(ghost, faint, ghost.get_rect(), border_radius=4)
        screen.blit(ghost, rect.topleft)
        pygame.draw.rect(screen, colour, rect, width=1, border_radius=4)


def draw_spike(screen, rect):
    """Draw a spiky red triangle that means 'danger'."""
    points = [
        (rect.left, rect.bottom),
        (rect.centerx, rect.top + 4),
        (rect.right, rect.bottom),
    ]
    pygame.draw.polygon(screen, COL_SPIKE, points)


def draw_gem(screen, rect):
    """Draw a sparkly diamond gem."""
    cx, cy = rect.center
    points = [(cx, cy - 9), (cx + 8, cy), (cx, cy + 9), (cx - 8, cy)]
    pygame.draw.polygon(screen, COL_GEM, points)
    pygame.draw.polygon(screen, (255, 255, 255), points, 1)


def draw_goal(screen, rect):
    """Draw the goal flag you are trying to reach."""
    pole_x = rect.left + 6
    pygame.draw.rect(screen, (230, 230, 230), (pole_x, rect.top + 2, 3, TILE - 4))
    flag = [(pole_x + 3, rect.top + 4),
            (rect.right - 2, rect.top + 10),
            (pole_x + 3, rect.top + 16)]
    pygame.draw.polygon(screen, COL_GOAL, flag)


def draw_checkpoint(screen, rect, active):
    """Draw a checkpoint flag. It glows brighter once you have touched it."""
    pole_x = rect.left + 6
    pygame.draw.rect(screen, (200, 200, 200), (pole_x, rect.top + 2, 3, TILE - 4))
    colour = COL_CHECKPOINT if active else (90, 80, 110)
    flag = [(pole_x + 3, rect.top + 6),
            (rect.right - 4, rect.top + 11),
            (pole_x + 3, rect.top + 16)]
    pygame.draw.polygon(screen, colour, flag)


def draw_level(screen, tiles, active_colour, collected, level_index, checkpoint_on):
    """Draw every square in the level."""
    for row in range(GRID_H):
        for col in range(GRID_W):
            letter = tiles[row][col]
            rect = tile_to_pixels(col, row)
            if letter == '#':
                draw_block(screen, rect, COL_GREY, True)
            elif letter == 'B':
                draw_block(screen, rect, COL_BLUE, active_colour == "BLUE")
            elif letter == 'P':
                draw_block(screen, rect, COL_PINK, active_colour == "PINK")
            elif letter == '^':
                draw_spike(screen, rect)
            elif letter == 'G':
                draw_goal(screen, rect)
            elif letter == 'C':
                draw_checkpoint(screen, rect, checkpoint_on)
            elif letter == '*':
                if (level_index, row, col) not in collected:
                    draw_gem(screen, rect)


def draw_player(screen, player):
    """Draw Star: a friendly square with two little eyes."""
    rect = player.rect()
    pygame.draw.rect(screen, PLAYER_COLOUR, rect, border_radius=6)
    # Eyes look in the direction she is facing.
    eye_y = rect.top + 9
    offset = 4 * player.facing
    pygame.draw.circle(screen, (20, 20, 20), (rect.centerx - 4 + offset, eye_y), 3)
    pygame.draw.circle(screen, (20, 20, 20), (rect.centerx + 4 + offset, eye_y), 3)


def draw_hud(screen, font, big_font, active_colour, level_index, gem_total, hint):
    """Draw the border (showing the active colour), the level name, and hints."""
    border_colour = COL_BLUE if active_colour == "BLUE" else COL_PINK
    # A thick coloured frame around the screen = the active colour, at a glance.
    thickness = 6
    pygame.draw.rect(screen, border_colour,
                     (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), thickness)

    # A little label in the top-left telling you the active colour.
    label = font.render("MODE: " + active_colour, True, border_colour)
    screen.blit(label, (16, 12))

    # The level number and name in the top-middle.
    names = ["First Steps", "Watch Your Step", "The Swap",
             "Mid-Air Magic", "The Gauntlet"]
    name = names[level_index] if level_index < len(names) else "Bonus"
    title = font.render("Level %d: %s" % (level_index + 1, name), True, COL_TEXT)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 12))

    # Gems collected so far, top-right.
    gems = font.render("Gems: %d" % gem_total, True, COL_GEM)
    screen.blit(gems, (SCREEN_WIDTH - gems.get_width() - 16, 12))

    # A friendly hint near the bottom, if there is one for this level.
    if hint:
        text = big_font.render(hint, True, COL_TEXT)
        box = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
        backdrop = box.inflate(24, 14)
        shade = pygame.Surface(backdrop.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 140))
        screen.blit(shade, backdrop.topleft)
        screen.blit(text, box)


def draw_overlay(screen, colour, alpha):
    """Cover the whole screen with a see-through colour (for flashes/fades)."""
    veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((colour[0], colour[1], colour[2], int(alpha)))
    screen.blit(veil, (0, 0))


# =============================================================================
#  THE TITLE SCREEN AND THE WIN SCREEN
# =============================================================================

def draw_title_screen(screen, title_font, font, big_font):
    """Show the game name, the controls, and 'press a key to start'."""
    draw_background(screen)

    title = title_font.render("COLOUR  SWAP", True, COL_TEXT)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 90))

    sub = font.render("Help %s jump between BLUE and PINK!" % PLAYER_NAME,
                      True, PLAYER_COLOUR)
    screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 160))

    # A little blue/pink colour sample so the idea is clear from the start.
    pygame.draw.rect(screen, COL_BLUE, (SCREEN_WIDTH // 2 - 90, 210, 70, 40),
                     border_radius=6)
    pygame.draw.rect(screen, COL_PINK, (SCREEN_WIDTH // 2 + 20, 210, 70, 40),
                     border_radius=6)

    controls = [
        "MOVE      Left / Right arrows   (or A / D)",
        "JUMP      Space   (or Up arrow)",
        "SWAP      Shift   (or X)",
        "RESTART   R          QUIT   Esc",
    ]
    y = 300
    for line in controls:
        text = big_font.render(line, True, COL_TEXT)
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
        y += 38

    press = font.render("Press any key to begin", True, COL_TEXT)
    screen.blit(press, (SCREEN_WIDTH // 2 - press.get_width() // 2, 470))


def draw_win_screen(screen, title_font, font, gem_total):
    """Show 'You Win!' and how many gems were collected."""
    draw_background(screen)
    win = title_font.render("YOU WIN!", True, COL_GOAL)
    screen.blit(win, (SCREEN_WIDTH // 2 - win.get_width() // 2, 180))

    star = font.render("Well done, %s!" % PLAYER_NAME, True, PLAYER_COLOUR)
    screen.blit(star, (SCREEN_WIDTH // 2 - star.get_width() // 2, 260))

    gems = font.render("Gems collected: %d" % gem_total, True, COL_GEM)
    screen.blit(gems, (SCREEN_WIDTH // 2 - gems.get_width() // 2, 310))

    press = font.render("Press any key to play again", True, COL_TEXT)
    screen.blit(press, (SCREEN_WIDTH // 2 - press.get_width() // 2, 400))


# =============================================================================
#  THE MAIN GAME
#  This is the heart of the game: it starts everything, then runs the big loop.
# =============================================================================

# This is "async" so it can run both on your computer AND inside a web browser.
async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Colour Swap")
    clock = pygame.time.Clock()

    # Fonts of three sizes for titles, normal text, and hints.
    title_font = pygame.font.SysFont(None, 84)
    font       = pygame.font.SysFont(None, 34)
    big_font   = pygame.font.SysFont(None, 28)

    # --- Game state (these change as you play) -------------------------------
    state = "TITLE"            # "TITLE", "PLAYING", or "WIN"
    level_index = 0
    collected_gems = set()     # which gems (level, row, col) have been taken

    # These get filled in by start_level().
    tiles = []
    player = Player(0, 0)
    active_colour = START_COLOUR
    spawn_col, spawn_row = 1, 1
    checkpoint_on = False
    coyote = 0
    jump_buffer = 0
    swap_flash = 0             # counts down after a swap (for the flash effect)
    respawn_flash = 0          # counts down after dying (for the quick fade)

    def place_player_at(col, row):
        """Put the hero neatly inside a square, standing on whatever is below."""
        player.x = col * TILE + (TILE - PLAYER_WIDTH) / 2
        player.y = row * TILE + (TILE - PLAYER_HEIGHT)
        player.vx = 0
        player.vy = 0

    def start_level(index):
        """Load a level and reset everything for a fresh attempt."""
        nonlocal tiles, spawn_col, spawn_row, active_colour
        nonlocal checkpoint_on, coyote, jump_buffer, swap_flash, respawn_flash
        tiles, spawn_col, spawn_row = load_level(index)
        place_player_at(spawn_col, spawn_row)
        active_colour = START_COLOUR
        checkpoint_on = False
        coyote = 0
        jump_buffer = 0
        swap_flash = 0
        respawn_flash = 0

    def respawn():
        """Send the hero back to the checkpoint (or the start) after dying."""
        nonlocal active_colour, respawn_flash
        place_player_at(spawn_col, spawn_row)
        active_colour = START_COLOUR     # always restart the puzzle in BLUE
        respawn_flash = 18               # show a quick fade

    # The hint shown on each level (only level 1 and the first swap level).
    def hint_for_level(index):
        if index == 0:
            return "Use the arrow keys to move and Space to jump!"
        if index == 2 and SWAP_KEY_HINT:
            return "New trick! Press SHIFT (or X) to swap BLUE and PINK."
        return None

    # ------------------------------------------------------------------ LOOP --
    running = True
    while running:
        # ----- 1. Handle key presses and the window's close button -----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif state == "TITLE":
                    # Any key starts a brand new game.
                    state = "PLAYING"
                    level_index = 0
                    collected_gems = set()
                    start_level(level_index)

                elif state == "WIN":
                    # Any key goes back to the title screen.
                    state = "TITLE"

                elif state == "PLAYING":
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        jump_buffer = BUFFER_FRAMES          # remember the press
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT,
                                       pygame.K_x):
                        # SWAP the active colour, with a little flash.
                        active_colour = "PINK" if active_colour == "BLUE" else "BLUE"
                        swap_flash = 12
                    elif event.key == pygame.K_r:
                        start_level(level_index)             # restart this level

        # ----- 2. Update the game (only while actually playing) --------------
        if state == "PLAYING":
            keys = pygame.key.get_pressed()

            # Sideways movement from the held keys.
            player.vx = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.vx = -PLAYER_SPEED
                player.facing = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.vx = PLAYER_SPEED
                player.facing = 1

            # Try to jump if a press is buffered AND we may still jump (coyote).
            if jump_buffer > 0 and coyote > 0:
                player.vy = -JUMP_STRENGTH
                player.on_ground = False
                coyote = 0
                jump_buffer = 0

            # Gravity pulls her down a little more each frame.
            player.vy += GRAVITY
            if player.vy > MAX_FALL_SPEED:
                player.vy = MAX_FALL_SPEED

            # Move and bump into platforms (sideways first, then up/down).
            move_horizontal(player, tiles, active_colour)
            move_vertical(player, tiles, active_colour)

            # Update the "coyote time" timer (the grace period for jumping).
            if player.on_ground:
                coyote = COYOTE_FRAMES
            else:
                coyote = max(0, coyote - 1)
            jump_buffer = max(0, jump_buffer - 1)
            swap_flash = max(0, swap_flash - 1)
            respawn_flash = max(0, respawn_flash - 1)

            # ----- 3. Check the special squares she is touching --------------

            # Spikes or falling off the bottom = a quick respawn.
            if find_touched_tiles(player, tiles, '^'):
                respawn()
            elif player.y > SCREEN_HEIGHT + 40:
                respawn()

            # Gems: collect any she touches (each one counts only once).
            for col, row in find_touched_tiles(player, tiles, '*'):
                collected_gems.add((level_index, row, col))

            # Checkpoints: from now on, respawn here instead of the start.
            for col, row in find_touched_tiles(player, tiles, 'C'):
                spawn_col, spawn_row = col, row
                checkpoint_on = True

            # Goal: finish the level! Go to the next one, or win the game.
            if find_touched_tiles(player, tiles, 'G'):
                level_index += 1
                if level_index >= len(LEVELS):
                    state = "WIN"
                else:
                    start_level(level_index)

        # ----- 4. Draw everything --------------------------------------------
        if state == "TITLE":
            draw_title_screen(screen, title_font, font, big_font)

        elif state == "WIN":
            draw_win_screen(screen, title_font, font, len(collected_gems))

        elif state == "PLAYING":
            draw_background(screen)
            draw_level(screen, tiles, active_colour, collected_gems,
                       level_index, checkpoint_on)
            draw_player(screen, player)
            draw_hud(screen, font, big_font, active_colour, level_index,
                     len(collected_gems), hint_for_level(level_index))

            # A quick white-ish flash when you swap, so the swap feels like an event.
            if swap_flash > 0:
                flash_colour = COL_BLUE if active_colour == "BLUE" else COL_PINK
                draw_overlay(screen, flash_colour, swap_flash * 10)

            # A quick dark-red fade when you respawn.
            if respawn_flash > 0:
                draw_overlay(screen, (200, 60, 60), respawn_flash * 9)

        pygame.display.flip()
        clock.tick(FPS)
        # Give the web browser a tiny moment to breathe each frame.
        # (On a normal computer this does nothing noticeable.)
        await asyncio.sleep(0)

    pygame.quit()


# This makes the game start when you run:  python game.py
if __name__ == "__main__":
    print("=" * 55)
    print(" COLOUR SWAP")
    print(" If the game does not open, install Pygame first:")
    print("     pip install pygame")
    print(" Then run it with:")
    print("     python game.py")
    print("=" * 55)
    asyncio.run(main())
