import random

class Tile:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f"{self.value} of {self.suit}"

class Mahjong:
    def __init__(self):
        self.tiles = self._create_tiles()
        self.players = {"Player 1": [], "Player 2": [], "Player 3": [], "Player 4": []}
        self.discard_pile = []
        self.current_player_index = 0

    def _create_tiles(self):
        suits = ["Dots", "Bamboos", "Characters"]
        values = list(range(1, 10))
        dragons = ["Red", "Green", "White"]
        winds = ["East", "South", "West", "North"]
        flowers = ["Plum", "Orchid", "Chrysanthemum", "Bamboo"]
        seasons = ["Spring", "Summer", "Autumn", "Winter"]

        tiles = []
        for suit in suits:
            for value in values:
                tiles.extend([Tile(suit, value)] * 4)

        for dragon in dragons:
            tiles.extend([Tile("Dragon", dragon)] * 4)

        for wind in winds:
            tiles.extend([Tile("Wind", wind)] * 4)

        for flower in flowers:
            tiles.append(Tile("Flower", flower))

        for season in seasons:
            tiles.append(Tile("Season", season))

        return tiles

    def shuffle_and_deal(self):
        random.shuffle(self.tiles)
        for _ in range(13):
            for player in self.players:
                self.players[player].append(self.tiles.pop())

    def play(self):
        self.shuffle_and_deal()
        players = list(self.players.keys())
        while True:
            current_player_name = players[self.current_player_index]
            current_player_hand = self.players[current_player_name]

            print(f"\n{current_player_name}'s turn.")
            print("Your hand:")
            for i, tile in enumerate(current_player_hand):
                print(f"{i + 1}. {tile}")

            drawn_tile = self.tiles.pop()
            print(f"You drew a {drawn_tile}")
            current_player_hand.append(drawn_tile)

            while True:
                try:
                    discard_index = int(input("Choose a tile to discard (1-14): ")) - 1
                    if 0 <= discard_index < len(current_player_hand):
                        break
                    else:
                        print("Invalid input. Please enter a number between 1 and 14.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            discarded_tile = current_player_hand.pop(discard_index)
            self.discard_pile.append(discarded_tile)
            print(f"You discarded a {discarded_tile}")

            if self.check_win(current_player_hand):
                print(f"{current_player_name} wins!")
                break

            self.current_player_index = (self.current_player_index + 1) % 4

    def check_win(self, hand):
        if len(hand) != 14:
            return False

        hand_copy = hand[:]
        for i in range(len(hand_copy) - 1):
            if hand_copy[i] == hand_copy[i+1]:
                pair = [hand_copy.pop(i), hand_copy.pop(i)]
                if self.is_valid_mahjong(hand_copy):
                    return True
                hand_copy.insert(i, pair[0])
                hand_copy.insert(i, pair[1])
        return False

    def is_valid_mahjong(self, hand):
        if not hand:
            return True

        hand.sort(key=lambda x: (x.suit, x.value))

        # Check for pungs
        if len(hand) >= 3 and hand[0] == hand[1] == hand[2]:
            if self.is_valid_mahjong(hand[3:]):
                return True

        # Check for chows
        if len(hand) >= 3 and hand[0].suit == hand[1].suit == hand[2].suit and hand[0].value == hand[1].value - 1 == hand[2].value - 2:
            if self.is_valid_mahjong(hand[3:]):
                return True

        return False


if __name__ == "__main__":
    game = Mahjong()
    game.play()
