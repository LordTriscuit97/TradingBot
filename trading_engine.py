import os
import pandas as pd


class TradingEngine:
    def __init__(self, portfolio, data_manager, strategy):
        self.portfolio = portfolio
        self.data_manager = data_manager
        self.strategy = strategy

    def _build_master_dataframe(self, tickers: list) -> pd.DataFrame:
        print("🔄 Construction de la matrice stable...")
        df_list = []
        for ticker in tickers:
            csv_path = os.path.join(self.data_manager.data_dir, f"{ticker}_history.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                # On ne garde que les tickers qui ont assez de données (ex: > 90% du temps)
                if len(df) > 400:
                    df = df.rename(columns={'Close': ticker})
                    df_list.append(df)

        master_df = pd.concat(df_list, axis=1)

        # REMPLACER dropna() PAR CECI :
        # On remplit les trous par la valeur précédente, puis par la suivante.
        # Ça évite de supprimer des journées entières de test.
        master_df = master_df.ffill().bfill()

        return master_df

    def _execute_orders(self, target_weights: dict, current_prices: dict):
        """
        Compare le portefeuille actuel avec les cibles et lance les transactions.
        """
        total_value = self.portfolio.get_total_value(current_prices)

        # 1. On effectue les VENTES en premier pour dégager de la liquidité
        for ticker, target_weight in target_weights.items():
            if ticker not in current_prices:
                continue

            price = current_prices[ticker]
            current_qty = self.portfolio.positions.get(ticker, 0.0)

            # Formule mathématique du rebalancement
            target_cash = total_value * target_weight
            target_qty = target_cash / price
            diff = target_qty - current_qty

            if diff < -0.0001:  # On en a trop, on vend
                qty_to_sell = abs(diff)
                print(f"🔴 VENTE  : {qty_to_sell:8.4f} {ticker} @ {price:.2f}$")
                self.portfolio.sell(ticker, price, qty_to_sell)

        # 2. On effectue les ACHATS avec le cash disponible
        for ticker, target_weight in target_weights.items():
            if ticker not in current_prices:
                continue

            price = current_prices[ticker]
            current_qty = self.portfolio.positions.get(ticker, 0.0)

            target_cash = total_value * target_weight
            target_qty = target_cash / price
            diff = target_qty - current_qty

            if diff > 0.0001:  # Il nous en manque, on achète
                qty_to_buy = diff
                print(f"🟢 ACHAT  : {qty_to_buy:8.4f} {ticker} @ {price:.2f}$")
                self.portfolio.buy(ticker, price, qty_to_buy)

    def run_daily_cycle(self):
        """
        La méthode principale. À exécuter une fois par jour.
        """
        print("\n⚙️ --- DÉMARRAGE DU CYCLE QUOTIDIEN ---")
        tickers = self.data_manager.get_top_100_tickers()

        # 1. Préparation des données
        price_matrix = self._build_master_dataframe(tickers)
        if price_matrix.empty:
            print("❌ Aucune donnée disponible.")
            return

        current_prices = price_matrix.iloc[-1].to_dict()

        # 2. Appel au cerveau (La stratégie)
        target_weights = self.strategy.get_target_weights(price_matrix)

        # 3. Exécution matérielle (Le portefeuille)
        self._execute_orders(target_weights, current_prices)

        # 4. Rapport
        final_value = self.portfolio.get_total_value(current_prices)
        cash_ratio = (self.portfolio.cash / final_value) * 100
        print(f"✅ Cycle terminé. Valeur Nette : {final_value:.2f}$ (Liquidité: {cash_ratio:.1f}%)")
        print("--------------------------------------\n")