import pygame
import sys

# Initialize pygame
pygame.init()

# Constants
BOARD_SIZE = 15
CELL_SIZE = 40
BOARD_PADDING = 50
STONE_RADIUS = CELL_SIZE // 2 - 2
WINDOW_WIDTH = BOARD_SIZE * CELL_SIZE + 2 * BOARD_PADDING
WINDOW_HEIGHT = BOARD_SIZE * CELL_SIZE + 2 * BOARD_PADDING + 60
BACKGROUND_COLOR = (220, 179, 92)
LINE_COLOR = (0, 0, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 128, 0)
HIGHLIGHT_COLOR = (100, 100, 255, 100)

# Set up the display
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Gomoku - Five in a Row")

# Font setup
font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 28)

class GomokuGame:
    def __init__(self):
        self.board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = 1  # 1 for black, 2 for white
        self.game_over = False
        self.winner = None
        self.last_move = None

    def make_move(self, row, col):
        if self.game_over or self.board[row][col] != 0:
            return False
        
        self.board[row][col] = self.current_player
        self.last_move = (row, col)
        
        if self.check_win(row, col):
            self.game_over = True
            self.winner = self.current_player
        elif self.is_board_full():
            self.game_over = True
            self.winner = 0  # Draw
        
        self.current_player = 3 - self.current_player  # Switch player (1->2, 2->1)
        return True

    def check_win(self, row, col):
        player = self.board[row][col]
        directions = [
            (0, 1),   # horizontal
            (1, 0),   # vertical
            (1, 1),   # diagonal /
            (1, -1)   # diagonal \
        ]
        
        for dr, dc in directions:
            count = 1  # Count the current stone
            
            # Check in positive direction
            r, c = row + dr, col + dc
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and self.board[r][c] == player:
                count += 1
                r += dr
                c += dc
            
            # Check in negative direction
            r, c = row - dr, col - dc
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and self.board[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            
            if count >= 5:
                return True
        return False

    def is_board_full(self):
        for row in self.board:
            if 0 in row:
                return False
        return True

    def reset(self):
        self.__init__()

def draw_board(game):
    # Draw background
    screen.fill(BACKGROUND_COLOR)
    
    # Draw board lines
    for i in range(BOARD_SIZE):
        # Horizontal lines
        pygame.draw.line(
            screen, 
            LINE_COLOR, 
            (BOARD_PADDING, BOARD_PADDING + i * CELL_SIZE),
            (WINDOW_WIDTH - BOARD_PADDING, BOARD_PADDING + i * CELL_SIZE),
            1
        )
        # Vertical lines
        pygame.draw.line(
            screen, 
            LINE_COLOR, 
            (BOARD_PADDING + i * CELL_SIZE, BOARD_PADDING),
            (BOARD_PADDING + i * CELL_SIZE, WINDOW_HEIGHT - BOARD_PADDING - 60),
            1
        )
    
    # Draw star points (hoshi)
    star_points = [3, 7, 11]
    for row in star_points:
        for col in star_points:
            pygame.draw.circle(
                screen,
                BLACK,
                (BOARD_PADDING + col * CELL_SIZE, BOARD_PADDING + row * CELL_SIZE),
                4
            )
    
    # Draw stones
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if game.board[row][col] != 0:
                color = BLACK if game.board[row][col] == 1 else WHITE
                pygame.draw.circle(
                    screen,
                    color,
                    (BOARD_PADDING + col * CELL_SIZE, BOARD_PADDING + row * CELL_SIZE),
                    STONE_RADIUS
                )
                # Draw outline for white stones
                if game.board[row][col] == 2:
                    pygame.draw.circle(
                        screen,
                        BLACK,
                        (BOARD_PADDING + col * CELL_SIZE, BOARD_PADDING + row * CELL_SIZE),
                        STONE_RADIUS,
                        1
                    )
    
    # Highlight last move
    if game.last_move:
        row, col = game.last_move
        pygame.draw.circle(
            screen,
            RED,
            (BOARD_PADDING + col * CELL_SIZE, BOARD_PADDING + row * CELL_SIZE),
            STONE_RADIUS // 3
        )

def draw_ui(game):
    # Draw player turn indicator
    if not game.game_over:
        player_text = "Black's Turn" if game.current_player == 1 else "White's Turn"
        color = BLACK if game.current_player == 1 else WHITE
        text_surface = font.render(player_text, True, color)
        screen.blit(text_surface, (WINDOW_WIDTH // 2 - text_surface.get_width() // 2, WINDOW_HEIGHT - 50))
        
        # Draw stone preview
        pygame.draw.circle(
            screen,
            color,
            (WINDOW_WIDTH // 2 + text_surface.get_width() // 2 + 30, WINDOW_HEIGHT - 45),
            STONE_RADIUS // 2
        )
        if game.current_player == 2:
            pygame.draw.circle(
                screen,
                BLACK,
                (WINDOW_WIDTH // 2 + text_surface.get_width() // 2 + 30, WINDOW_HEIGHT - 45),
                STONE_RADIUS // 2,
                1
            )
    else:
        if game.winner == 0:
            text_surface = font.render("Game Over: Draw!", True, GREEN)
        else:
            winner_text = "Black Wins!" if game.winner == 1 else "White Wins!"
            color = BLACK if game.winner == 1 else WHITE
            text_surface = font.render(winner_text, True, color)
        screen.blit(text_surface, (WINDOW_WIDTH // 2 - text_surface.get_width() // 2, WINDOW_HEIGHT - 50))
        
        # Draw restart instruction
        restart_text = small_font.render("Press R to restart", True, BLUE)
        screen.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, WINDOW_HEIGHT - 25))

def main():
    game = GomokuGame()
    clock = pygame.time.Clock()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN and not game.game_over:
                x, y = event.pos
                # Convert mouse position to board coordinates
                col = round((x - BOARD_PADDING) / CELL_SIZE)
                row = round((y - BOARD_PADDING) / CELL_SIZE)
                
                # Check if the click is within the board
                if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
                    game.make_move(row, col)
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()
        
        draw_board(game)
        draw_ui(game)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()