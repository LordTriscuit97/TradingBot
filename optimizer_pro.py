import yfinance as yf
import pandas as pd
import numpy as np
from tqdm import tqdm
from pykalman import KalmanFilter
# On importe explicitement les 3 stratégies pour éviter le NameError
from strategies import StrategyKalman, StrategyZScore, StrategyBreakout

# --- 1. CONFIGURATION ET DONNÉES ---
SP20_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'LLY', 'AVGO',
    'JPM', 'XOM', 'UNH', 'V', 'PG', 'MA', 'JNJ', 'HD', 'MRK', 'COST'
]

print(f"📥 Téléchargement des données 2020-2024 pour {len(SP20_TICKERS)} sociétés...")
# Téléchargement optimisé
raw_data = yf.download(SP20_TICKERS, start='2020-01-01', end='2024-12-31', group_by='ticker', progress=False)

print("🔄 Conversion en données HEBDOMADAIRES (Weekly)...")
weekly_data = raw_data.resample('W-FRI').last()


# --- 2. FONCTIONS DE SIMULATION ---

def pre_calcul_kalman(prices, sensibilite):
    """Calcul vectoriel instantané pour Kalman"""
    kf = KalmanFilter(transition_matrices=[1], observation_matrices=[1],
                      initial_state_mean=prices.iloc[0], initial_state_covariance=1,
                      observation_covariance=1, transition_covariance=0.01)
    state_means, _ = kf.filter(prices.values)
    kalman_curve = pd.Series(state_means.flatten(), index=prices.index)
    pente = kalman_curve.diff()

    signals = np.where(pente > sensibilite, 1, 0)
    signals = np.where(pente < -sensibilite, -1, signals)
    return pd.Series(signals, index=prices.index)


def backtest_vectoriel(signals_dict, data_prices):
    """Moteur ultra-rapide utilisant les signaux pré-calculés"""
    cash = 100000.0
    positions = {}
    dates = data_prices.index
    tickers = signals_dict.keys()

    for i in range(1, len(dates)):
        date = dates[i]
        date_prev = dates[i - 1]

        for symbol in tickers:
            try:
                # Récupération Prix
                try:
                    prix = float(data_prices[symbol]['Close'].loc[date])
                except:
                    prix = float(data_prices.xs(symbol, level=0, axis=1)['Close'].iloc[i])

                # Récupération Signal
                if symbol not in signals_dict: continue
                try:
                    signal = signals_dict[symbol].loc[date_prev]
                except:
                    continue

                mise = 2000.0

                if signal == 1 and cash >= mise and symbol not in positions:
                    qte = mise / prix
                    positions[symbol] = qte
                    cash -= mise
                elif signal == -1 and symbol in positions:
                    cash += positions[symbol] * prix
                    del positions[symbol]
            except:
                continue

    valeur = cash
    for s, q in positions.items():
        try:
            try:
                p = float(data_prices[s]['Close'].iloc[-1])
            except:
                p = float(data_prices.xs(s, level=0, axis=1)['Close'].iloc[-1])
            valeur += q * p
        except:
            pass
    return valeur


def backtest_standard(strategie):
    """Moteur standard pour Z-Score et Breakout (suffisamment rapide ici)"""
    cash = 100000.0
    positions = {}
    dates = weekly_data.index

    for i in range(20, len(dates)):
        # On ne traite pas tout le code à chaque fois pour aller vite
        # On prend juste le slice nécessaire
        try:
            # Astuce pour accélérer : on prend les données du jour
            row = weekly_data.iloc[i]
        except:
            continue

        for symbol in SP20_TICKERS:
            try:
                # Extraction historique (nécessaire pour calculer l'indicateur)
                if isinstance(weekly_data.columns, pd.MultiIndex):
                    hist = weekly_data[symbol]['Close'].iloc[:i]
                    prix = float(weekly_data[symbol]['Close'].iloc[i])
                else:
                    hist = weekly_data.xs(symbol, level=0, axis=1)['Close'].iloc[:i]
                    prix = float(hist.iloc[-1])

                if pd.isna(prix): continue

                sig = strategie.analyser(hist)

                if sig == 1 and cash >= 2000 and symbol not in positions:
                    positions[symbol] = 2000 / prix;
                    cash -= 2000
                elif sig == -1 and symbol in positions:
                    cash += positions[symbol] * prix;
                    del positions[symbol]
            except:
                continue

    valeur = cash
    for s, q in positions.items():
        try:
            if isinstance(weekly_data.columns, pd.MultiIndex):
                p = float(weekly_data[s]['Close'].iloc[-1])
            else:
                p = float(weekly_data.xs(s, level=0, axis=1)['Close'].iloc[-1])
            valeur += q * p
        except:
            pass
    return valeur


# --- 3. L'OPTIMISATION (Le cœur du script) ---

print("\n--- ⚡ 1. Optimisation KALMAN (Vectoriel) ---")
best_score = 0
best_k = 0
# De 0.01 à 0.25 par pas de 0.01
for s in tqdm([i / 100 for i in range(1, 26, 1)]):
    all_signals = {}
    for t in SP20_TICKERS:
        try:
            if isinstance(weekly_data.columns, pd.MultiIndex):
                prices = weekly_data[t]['Close']
            else:
                prices = weekly_data.xs(t, level=0, axis=1)['Close']
            all_signals[t] = pre_calcul_kalman(prices.dropna(), s)
        except:
            continue

    res = backtest_vectoriel(all_signals, weekly_data)
    if res > best_score:
        best_score = res
        best_k = s
print(f"🏆 MEILLEUR KALMAN : Seuil = {best_k} (Cash: {best_score:.0f}$)")

print("\n--- ⚡ 2. Optimisation Z-SCORE (Standard) ---")
best_score = 0
best_z = (0, 0)
import itertools

# Fenêtres : 4 à 20 semaines | Seuils : 1.5 à 3.0
params_z = list(itertools.product([4, 8, 12, 20], [1.5, 2.0, 2.5, 3.0]))

for fen, seuil in tqdm(params_z):
    strat = StrategyZScore(fenetre=fen, seuil=seuil)
    res = backtest_standard(strat)
    if res > best_score:
        best_score = res
        best_z = (fen, seuil)
print(f"🏆 MEILLEUR Z-SCORE : Fenêtre={best_z[0]}, Seuil={best_z[1]} (Cash: {best_score:.0f}$)")

print("\n--- ⚡ 3. Optimisation BREAKOUT (Standard) ---")
best_score = 0
best_b = 0
# Fenêtres : 4 à 52 semaines
for f in tqdm([4, 8, 12, 20, 30, 40, 52]):
    strat = StrategyBreakout(fenetre=f)
    res = backtest_standard(strat)
    if res > best_score:
        best_score = res
        best_b = f
print(f"🏆 MEILLEUR BREAKOUT : Fenêtre = {best_b} semaines (Cash: {best_score:.0f}$)")

print("\n✅ OPTIMISATION TERMINÉE. Note ces 3 résultats pour le Dashboard !")