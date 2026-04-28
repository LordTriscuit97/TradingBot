import json
import os


class Portfolio:
    def __init__(self, save_file: str = "portfolio_state.json"):
        self.save_file = save_file

        self.cash = 0.0
        self.positions = {}

        self._initialiser_compte()

    def _initialiser_compte(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, 'r') as file:
                try:
                    data = json.load(file)
                    self.cash = data.get("cash", 0.0)
                    self.positions = data.get("positions", {})
                    print(f"Portefeuille chargé : {self.cash:.2f}$ en cash, {len(self.positions)} positions.")
                except json.JSONDecodeError:
                    print("⚠Fichier corrompu. Réinitialisation des fonds.")
                    self._creer_nouveau_compte()
        else:
            self._creer_nouveau_compte()

    def _creer_nouveau_compte(self):
        self.cash = 10000.0
        self.positions = {}
        print(f"Nouveau compte créé. Montant initial verrouillé à {self.cash:.2f}$.")
        self.save_state()

    def buy(self, ticker: str, price: float, quantity: float) -> bool:
        cost = price * quantity
        if self.cash >= cost:
            self.cash -= cost
            self.positions[ticker] = self.positions.get(ticker, 0.0) + quantity
            self.save_state()
            return True

        print(f"Fonds insuffisants pour acheter {quantity} parts de {ticker}.")
        return False

    def sell(self, ticker: str, price: float, quantity: float) -> bool:
        if ticker in self.positions and self.positions[ticker] >= quantity:
            self.cash += price * quantity
            self.positions[ticker] -= quantity

            if self.positions[ticker] < 0.0001:
                del self.positions[ticker]

            self.save_state()
            return True

        print(f"Impossible de vendre {quantity} parts de {ticker}.")
        return False

    def get_total_value(self, current_prices: dict) -> float:
        total_value = self.cash
        for ticker, qty in self.positions.items():
            if ticker in current_prices:
                total_value += qty * current_prices[ticker]
        return total_value

    def save_state(self):
        data_to_save = {
            "cash": self.cash,
            "positions": self.positions
        }
        with open(self.save_file, 'w') as file:
            json.dump(data_to_save, file, indent=4)