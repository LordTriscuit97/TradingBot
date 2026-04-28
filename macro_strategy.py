import numpy as np
import pandas as pd


class MacroStrategy:
    def __init__(self):
        # --- C'EST CE BLOC QUI MANQUAIT OU ÉTAIT INCOMPLET ---
        self.lookback_total = 252  # 1 an de jours de bourse
        self.lookback_skip = 21  # 1 mois d'exclusion (pour purger la réversion)
        self.top_n = 10  # On garde le top 10 des gagnants
        # ----------------------------------------------------

    def get_target_weights(self, price_matrix: pd.DataFrame) -> dict:
        """
        Calcule l'allocation basée sur le Momentum et le demi-Critère de Kelly.
        """
        # 1. Vérification de la maturité des données (Le fameux lookback_total)
        if len(price_matrix) < self.lookback_total:
            return {ticker: 0.0 for ticker in price_matrix.columns}

        # 2. Calcul du Momentum (Rendement 1 an moins le dernier mois)
        # On utilise .iloc pour pointer les lignes exactes dans la matrice
        p_recent = price_matrix.iloc[-self.lookback_skip]
        p_old = price_matrix.iloc[-self.lookback_total]

        momentum = (p_recent / p_old) - 1.0

        # 3. Sélection des champions
        top_assets = momentum.nlargest(self.top_n).index

        if len(top_assets) == 0:
            return {ticker: 0.0 for ticker in price_matrix.columns}

        # 4. Calcul de l'allocation (Kelly simplifié)
        recent_prices = price_matrix[top_assets].tail(self.lookback_total)
        # Rendements logarithmiques pour les stats
        returns = np.log(recent_prices / recent_prices.shift(1)).dropna()

        mu = returns.mean() * 252  # Moyenne annualisée
        var = returns.var() * 252  # Variance annualisée

        # Formule de Kelly : (Espérance / Variance) / 2
        kelly_weights = mu / var
        kelly_weights = kelly_weights / 2.0

        # On s'assure qu'on ne vend pas à découvert (pas de poids négatifs)
        kelly_weights[kelly_weights < 0] = 0.0

        # 5. Normalisation (Pas d'emprunt, max 100% du cash)
        total_sum = kelly_weights.sum()
        if total_sum > 1.0:
            final_weights = kelly_weights / total_sum
        else:
            final_weights = kelly_weights

        # 6. Construction du dictionnaire final pour le TradingEngine
        target_dict = {ticker: 0.0 for ticker in price_matrix.columns}
        for ticker in top_assets:
            target_dict[ticker] = final_weights[ticker]

        return target_dict