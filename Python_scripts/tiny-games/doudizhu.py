import pygame
import sys
import random
from collections import Counter

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
CARD_WIDTH = 80
CARD_HEIGHT = 120
CARD_SPACING = 25
HAND_SPACING = 30
BACKGROUND_COLOR = (20, 120, 50)
TEXT_COLOR = (255, 255, 255)
HIGHLIGHT_COLOR = (255, 255, 0, 100)
FONT_SIZE = 24
LARGE_FONT_SIZE = 36

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dou Di Zhu - Landlord's Game")
clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont(None, FONT_SIZE)
large_font = pygame.font.SysFont(None, LARGE_FONT_SIZE)

# Card suits and ranks
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
SPECIAL_RANKS = ['Small Joker', 'Big Joker']

# Card values for comparison (3 is lowest, 2 is highest, then jokers)
CARD_VALUES = {rank: i for i, rank in enumerate(RANKS + ['Small Joker', 'Big Joker'])}

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = CARD_VALUES[rank]
        self.selected = False

    def __str__(self):
        return f"{self.suit}{self.rank}" if self.suit else self.rank

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __lt__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.value < other.value

    def __hash__(self):
        return hash((self.suit, self.rank))

class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.hand = []
        self.is_human = is_human
        self.is_landlord = False

    def add_cards(self, cards):
        self.hand.extend(cards)
        self.sort_hand()

    def sort_hand(self):
        self.hand.sort()

    def play_cards(self, cards_to_play):
        # Ensure cards_to_play are actually in hand
        for card in cards_to_play:
            if card not in self.hand:
                return False # Invalid play, card not in hand
        
        for card in cards_to_play:
            self.hand.remove(card)
        return cards_to_play

class Game:
    def __init__(self):
        self.deck = self.create_deck()
        self.players = [Player("Player", True), Player("AI 1"), Player("AI 2")]
        self.landlord = None
        self.current_player_index = 0
        self.last_played_cards = []
        self.last_player_index = -1
        self.pass_count = 0
        self.game_over = False
        self.winner = None
        self.state = "dealing"  # dealing, bidding, playing, game_over
        self.trump_cards = []  # Three extra cards for landlord

    def create_deck(self):
        deck = []
        for suit in SUITS:
            for rank in RANKS:
                deck.append(Card(suit, rank))
        deck.append(Card("", "Small Joker"))
        deck.append(Card("", "Big Joker"))
        return deck

    def shuffle_and_deal(self):
        random.shuffle(self.deck)
        for i in range(3):
            self.players[i].hand = self.deck[i*17:(i+1)*17]
            self.players[i].sort_hand()
        self.trump_cards = self.deck[51:54]
        self.state = "bidding" # Transition to bidding phase

    def determine_landlord(self):
        # Simplified landlord determination: Player 1 is landlord for now
        # In a real game, this involves bidding rounds
        self.landlord = self.players[0] 
        self.landlord.is_landlord = True
        self.landlord.add_cards(self.trump_cards)
        self.current_player_index = self.players.index(self.landlord)
        self.state = "playing"

    def get_current_player(self):
        return self.players[self.current_player_index]

    def next_player(self):
        self.current_player_index = (self.current_player_index + 1) % 3

    def play_cards(self, cards):
        current_player = self.get_current_player()
        
        # Validate move
        if not self.is_valid_play(cards, self.last_played_cards):
            return False
        
        # Play the cards
        played = current_player.play_cards(cards)
        if played is False: # Cards not in hand
            return False

        self.last_played_cards = played
        self.last_player_index = self.current_player_index
        self.pass_count = 0 # Reset pass count after a valid play
        
        # Check for win
        if len(current_player.hand) == 0:
            self.game_over = True
            self.winner = current_player
            self.state = "game_over"
        else:
            self.next_player()
        
        return True

    def pass_turn(self):
        self.pass_count += 1
        # If everyone passes (2 passes after a play), reset last_played_cards
        if self.pass_count >= 2 and self.last_played_cards:
            self.last_played_cards = []
            self.pass_count = 0 # Reset pass count
        self.next_player()

    def is_valid_play(self, cards, last_cards):
        if not cards:
            return False # Cannot play empty set of cards

        # If this is the first play of a round or everyone passed
        if not last_cards:
            return self.get_combination_type(cards) != "invalid"
        
        # If it's the same player playing again (e.g., after others passed)
        if self.last_player_index == self.current_player_index:
            return self.get_combination_type(cards) != "invalid"
        
        # Check if the new play beats the last play
        return self.beats_last_play(cards, last_cards)

    def get_combination_type(self, cards):
        num_cards = len(cards)
        ranks = sorted([card.value for card in cards])
        rank_counts = Counter(ranks)
        unique_ranks = sorted(rank_counts.keys())

        # Single
        if num_cards == 1:
            return "single"

        # Pair
        if num_cards == 2 and len(unique_ranks) == 1:
            return "pair"
                # Joker Bomb (Small Joker + Big Joker)
        if num_cards == 2 and {card.rank for card in cards} == {"Small Joker", "Big Joker"}:
            return "joker_bomb"

        # Three of a kind
        if num_cards == 3 and len(unique_ranks) == 1:
            return "three"

        # Bomb (Four of a kind)
        if num_cards == 4 and len(unique_ranks) == 1:
            return "bomb"
        # Three with one
        if num_cards == 4 and len(unique_ranks) == 2 and 3 in rank_counts.values():
            return "three_one"

        # Straight (Shun Zi) - 5 or more consecutive cards, no 2s or Jokers
        if num_cards >= 5 and len(unique_ranks) == num_cards:
            # Check for consecutive values
            is_consecutive = all(unique_ranks[i] == unique_ranks[i-1] + 1 for i in range(1, num_cards))
            # Check for 2s or Jokers
            has_invalid_ranks = any(card.rank in {'2', 'Small Joker', 'Big Joker'} for card in cards)
            if is_consecutive and not has_invalid_ranks:
                return "straight"

        # Full House (San Dai Er) - Three of a kind with a pair
        if num_cards == 5 and len(unique_ranks) == 2 and 3 in rank_counts.values() and 2 in rank_counts.values():
            return "full_house"
        
        # Other combinations (e.g., Three with pair, Four with two singles, Four with two pairs, Airplane, etc.)
        # For simplicity, only implementing basic ones for now.
        # This part would need significant expansion for a full Dou Di Zhu game.

        return "invalid"

    def beats_last_play(self, new_cards, last_cards):
        new_type = self.get_combination_type(new_cards)
        last_type = self.get_combination_type(last_cards)

        if new_type == "invalid":
            return False

        # Joker Bomb beats everything except another Joker Bomb (which is impossible)
        if new_type == "joker_bomb":
            return True
        
        # Bomb beats everything except Joker Bomb or a larger Bomb
        if new_type == "bomb":
            if last_type == "joker_bomb":
                return False
            if last_type == "bomb":
                return max(new_cards).value > max(last_cards).value
            return True # Bomb beats any non-bomb, non-joker_bomb combination

        # If types don't match (and not a bomb/joker_bomb scenario), it's an invalid play
        if new_type != last_type:
            return False

        # Compare based on type
        if new_type in ["single", "pair", "three", "straight", "full_house", "three_one"]:
            # For these types, compare the highest card's value
            return max(new_cards).value > max(last_cards).value
        
        return False # Should not reach here if all types are handled

    def reset(self):
        self.__init__()
        self.shuffle_and_deal()
        self.determine_landlord() # Simplified for now

    def ai_play(self):
        current_player = self.get_current_player()
        if current_player.is_human:
            return # Human player, wait for input

        # Simple AI: Try to play a single card, then a pair, then pass
        # This AI is very basic and will not play complex combinations
        
        # If it's the first play of a round or everyone passed
        if not self.last_played_cards or self.last_player_index == self.current_player_index:
            # Try to play the smallest single card
            if current_player.hand:
                card_to_play = [current_player.hand[0]]
                if self.is_valid_play(card_to_play, []):
                    return self.play_cards(card_to_play)
            # If no single card, try smallest pair
            for i in range(len(current_player.hand) - 1):
                if current_player.hand[i].rank == current_player.hand[i+1].rank:
                    pair_to_play = [current_player.hand[i], current_player.hand[i+1]]
                    if self.is_valid_play(pair_to_play, []):
                        return self.play_cards(pair_to_play)
            # If nothing to play, pass
            self.pass_turn()
            return True
        else:
            # Try to beat the last play
            last_type = self.get_combination_type(self.last_played_cards)
            last_value = max(self.last_played_cards).value

            # Try to find a single card to beat
            if last_type == "single":
                for card in current_player.hand:
                    if card.value > last_value:
                        if self.play_cards([card]):
                            return True
            # Try to find a pair to beat
            elif last_type == "pair":
                for i in range(len(current_player.hand) - 1):
                    if current_player.hand[i].rank == current_player.hand[i+1].rank:
                        pair_to_play = [current_player.hand[i], current_player.hand[i+1]]
                        if max(pair_to_play).value > last_value:
                            if self.play_cards(pair_to_play):
                                return True
            # Try to find a bomb to beat anything
            # This is a very simple bomb check, could be improved
            for rank_val, count in Counter([c.value for c in current_player.hand]).items():
                if count == 4:
                    bomb_cards = [c for c in current_player.hand if c.value == rank_val]
                    if self.beats_last_play(bomb_cards, self.last_played_cards):
                        if self.play_cards(bomb_cards):
                            return True
            
            # Try to play a Joker Bomb
            joker_bomb_cards = []
            has_small_joker = False
            has_big_joker = False
            for card in current_player.hand:
                if card.rank == "Small Joker":
                    has_small_joker = True
                    joker_bomb_cards.append(card)
                elif card.rank == "Big Joker":
                    has_big_joker = True
                    joker_bomb_cards.append(card)
            if has_small_joker and has_big_joker:
                if self.beats_last_play(joker_bomb_cards, self.last_played_cards):
                    if self.play_cards(joker_bomb_cards):
                        return True

            # If no valid play found, pass
            self.pass_turn()
            return True


def draw_card(surface, card, x, y, selected=False):
    # Draw card background
    color = (255, 255, 255) if not selected else (255, 255, 200)
    pygame.draw.rect(surface, color, (x, y, CARD_WIDTH, CARD_HEIGHT), border_radius=10)
    pygame.draw.rect(surface, (0, 0, 0), (x, y, CARD_WIDTH, CARD_HEIGHT), 2, border_radius=10)
    
    # Draw card content
    text_color = (0, 0, 0)
    if card.suit in ['♥', '♦']:
        text_color = (255, 0, 0)
    
    # Rank text
    rank_text = font.render(card.rank, True, text_color)
    surface.blit(rank_text, (x + 5, y + 5))
    
    # Suit text (for regular cards)
    if card.suit:
        suit_text = font.render(card.suit, True, text_color)
        surface.blit(suit_text, (x + 5, y + 25))
    
    # Center suit for face cards and jokers
    if card.rank in ['J', 'Q', 'K', 'A', '2', 'Small Joker', 'Big Joker'] and card.suit:
        suit_large = pygame.font.SysFont(None, 48).render(card.suit, True, text_color)
        surface.blit(suit_large, (x + CARD_WIDTH//2 - suit_large.get_width()//2, 
                                  y + CARD_HEIGHT//2 - suit_large.get_height()//2))
    elif not card.suit: # For jokers, center their rank
        rank_large = pygame.font.SysFont(None, 48).render(card.rank, True, text_color)
        surface.blit(rank_large, (x + CARD_WIDTH//2 - rank_large.get_width()//2, 
                                  y + CARD_HEIGHT//2 - rank_large.get_height()//2))


def draw_hand(surface, player, x, y, show_cards=True):
    if not show_cards and not player.is_human:
        # Draw back of cards for AI players
        for i in range(len(player.hand)):
            pygame.draw.rect(surface, (0, 50, 150), 
                            (x + i * CARD_SPACING, y, CARD_WIDTH, CARD_HEIGHT), 
                            border_radius=10)
            pygame.draw.rect(surface, (0, 0, 0), 
                            (x + i * CARD_SPACING, y, CARD_WIDTH, CARD_HEIGHT), 
                            2, border_radius=10)
    else:
        # Draw actual cards
        for i, card in enumerate(player.hand):
            card_y = y - 20 if card.selected else y
            draw_card(surface, card, x + i * CARD_SPACING, card_y, card.selected)

def draw_game_state(surface, game):
    # Draw background
    surface.fill(BACKGROUND_COLOR)
    
    # Draw title
    title = large_font.render("Dou Di Zhu - Landlord's Game", True, TEXT_COLOR)
    surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 20))
    
    # Draw trump cards (only visible after landlord is determined)
    if game.state == "playing" and game.landlord:
        trump_text = font.render("Landlord's Cards:", True, TEXT_COLOR)
        surface.blit(trump_text, (SCREEN_WIDTH//2 - 100, 80))
        for i, card in enumerate(game.trump_cards):
            draw_card(surface, card, SCREEN_WIDTH//2 + i * CARD_SPACING - 50, 80)
    
    # Draw players and their hands
    # Player (bottom)
    player = game.players[0]
    player_text = font.render(f"{player.name} ({len(player.hand)} cards)" + (" - Landlord" if player.is_landlord else ""), True, TEXT_COLOR)
    surface.blit(player_text, (50, SCREEN_HEIGHT - 200))
    draw_hand(surface, player, 50, SCREEN_HEIGHT - 170, True)
    
    # AI 1 (left)
    ai1 = game.players[1]
    ai1_text = font.render(f"{ai1.name} ({len(ai1.hand)} cards)" + (" - Landlord" if ai1.is_landlord else ""), True, TEXT_COLOR)
    surface.blit(ai1_text, (50, 150))
    draw_hand(surface, ai1, 50, 180, False)  # Hide AI 1's cards
    
    # AI 2 (right)
    ai2 = game.players[2]
    ai2_text = font.render(f"{ai2.name} ({len(ai2.hand)} cards)" + (" - Landlord" if ai2.is_landlord else ""), True, TEXT_COLOR)
    surface.blit(ai2_text, (SCREEN_WIDTH - 250, 150))
    draw_hand(surface, ai2, SCREEN_WIDTH - 250, 180, False)  # Hide AI 2's cards
    
    # Draw last played cards
    if game.last_played_cards:
        last_player = game.players[game.last_player_index]
        last_text = font.render(f"Last played by {last_player.name}:", True, TEXT_COLOR)
        surface.blit(last_text, (SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 - 100))
        for i, card in enumerate(game.last_played_cards):
            draw_card(surface, card, SCREEN_WIDTH//2 + i * CARD_SPACING - 100, SCREEN_HEIGHT//2 - 50)
    
    # Draw current player indicator
    if game.state == "playing" and not game.game_over:
        current_player = game.get_current_player()
        indicator = font.render(f"Current Player: {current_player.name}", True, (255, 255, 0))
        surface.blit(indicator, (SCREEN_WIDTH//2 - indicator.get_width()//2, SCREEN_HEIGHT - 300))
    
    # Draw game state messages
    if game.state == "dealing":
        state_text = font.render("Dealing cards...", True, TEXT_COLOR)
        surface.blit(state_text, (SCREEN_WIDTH//2 - state_text.get_width()//2, SCREEN_HEIGHT//2))
    elif game.state == "bidding":
        state_text = font.render("Determining Landlord...", True, TEXT_COLOR)
        surface.blit(state_text, (SCREEN_WIDTH//2 - state_text.get_width()//2, SCREEN_HEIGHT//2))
    elif game.state == "game_over":
        if game.winner:
            winner_text = large_font.render(f"{game.winner.name} wins!", True, (255, 255, 0))
            surface.blit(winner_text, (SCREEN_WIDTH//2 - winner_text.get_width()//2, SCREEN_HEIGHT//2))
        restart_text = font.render("Press R to restart game", True, TEXT_COLOR)
        surface.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
    
    # Draw instructions
    instructions = [
        "Instructions:",
        "Click to select/deselect cards",
        "Press SPACE to play cards, P to pass",
        "Press R to restart game"
    ]
    for i, line in enumerate(instructions):
        text = font.render(line, True, TEXT_COLOR)
        surface.blit(text, (SCREEN_WIDTH - 300, SCREEN_HEIGHT - 150 + i * 30))

def main():
    game = Game()
    game.shuffle_and_deal()
    game.determine_landlord() # Simplified: Player 1 is always landlord for now
    
    selected_cards = []
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()
                    selected_cards = []
                elif event.key == pygame.K_p and game.state == "playing" and not game.game_over:
                    # Pass turn
                    current_player = game.get_current_player()
                    if current_player.is_human:
                        game.pass_turn()
                        # Clear selected cards after passing
                        for card in selected_cards:
                            card.selected = False
                        selected_cards = []
                elif event.key == pygame.K_SPACE and game.state == "playing" and not game.game_over:
                    # Play selected cards
                    current_player = game.get_current_player()
                    if current_player.is_human and selected_cards:
                        # Sort cards before playing to handle combinations correctly
                        if game.play_cards(sorted(selected_cards)):
                            # Clear selected cards after successful play
                            for card in selected_cards:
                                card.selected = False
                            selected_cards = []
            
            if event.type == pygame.MOUSEBUTTONDOWN and game.state == "playing" and not game.game_over:
                # Handle card selection for human player
                current_player = game.get_current_player()
                if current_player.is_human:
                    x, y = event.pos
                    player_hand_start_x = 50
                    player_hand_start_y = SCREEN_HEIGHT - 170
                    
                    # Iterate through cards from right to left to handle overlaps
                    for i in range(len(current_player.hand) - 1, -1, -1):
                        card = current_player.hand[i]
                        card_x = player_hand_start_x + i * CARD_SPACING
                        # Adjust y-coordinate for selected cards
                        card_y = player_hand_start_y - 20 if card.selected else player_hand_start_y
                        
                        card_rect = pygame.Rect(card_x, card_y, CARD_WIDTH, CARD_HEIGHT)

                        if card_rect.collidepoint(x, y):
                            card.selected = not card.selected
                            if card.selected:
                                selected_cards.append(card)
                            else:
                                if card in selected_cards:
                                    selected_cards.remove(card)
                            break  # Stop after handling the topmost card

        # AI turn
        if game.state == "playing" and not game.game_over and not game.get_current_player().is_human:
            game.ai_play()
            # Small delay for AI to make it visible
            pygame.time.wait(500)
        
        draw_game_state(screen, game)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
