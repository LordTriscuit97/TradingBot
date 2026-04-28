import os
import pandas as pd
from data_manager import DataManager
from portfolio import Portfolio
from macro_strategy import MacroStrategy
from trading_engine import TradingEngine

print("🚀 INITIALISATION DU SYSTÈME DE BACKTEST...")

# 1. Configuration temporelle
# On télécharge à partir de 2024 pour avoir le recul nécessaire
DATA_START = "2024-01-01"
# On simule les transactions uniquement sur 2025
SIM_START = "2025-01-01"
SIM_END = "2026-04-26"

# 2. Setup de l'environnement
test_file = "backtest_2025_state.json"
if os.path.exists(test_file):
    os.remove(test_file)

dm = DataManager()
port = Portfolio(save_file=test_file)
strategy = MacroStrategy()  # Utilise ton nouveau cerveau (Kelly/Momentum)
trader = TradingEngine(portfolio=port, data_manager=dm, strategy=strategy)

# 3. Acquisition des données + Benchmark
tickers = dm.get_top_100_tickers()
# On ajoute le SPY à la liste pour la comparaison
all_tickers = tickers + ["SPY"]
dm.update_historical_data(all_tickers, DATA_START, SIM_END)

# 4. Préparation de la simulation
full_matrix = trader._build_master_dataframe(all_tickers)
if full_matrix.empty:
    print("❌ Erreur : Matrice vide.")
    exit()

# Séparer le SPY de la matrice de trading
spy_prices = full_matrix["SPY"]
trading_matrix = full_matrix.drop(columns=["SPY"])

trading_days = trading_matrix.loc[SIM_START:SIM_END].index
print(f"⏳ Simulation : {len(trading_days)} jours.")

equity_curve = []
spy_curve = []

# ==========================================
# LA BOUCLE TEMPORELLE
# ==========================================
# Prix du SPY au tout début du backtest pour normaliser à 10 000$
spy_start_price = spy_prices.loc[trading_days[0]]

for current_date in trading_days:
    historical_slice = trading_matrix.loc[:current_date]
    current_prices = historical_slice.iloc[-1].to_dict()

    # Bot Execution
    target_weights = strategy.get_target_weights(historical_slice)
    trader._execute_orders(target_weights, current_prices)

    # Valeur du Bot
    valeur_bot = port.get_total_value(current_prices)
    equity_curve.append(valeur_bot)

    # Valeur du S&P 500 (Normalisée à 10k$)
    # Formule : (Prix Actuel / Prix Initial) * 10 000
    valeur_spy = (spy_prices.loc[current_date] / spy_start_price) * 10000
    spy_curve.append(valeur_spy)

# ==========================================
# BILAN FINAL : BOT vs S&P 500
# ==========================================
rendement_bot = ((equity_curve[-1] - 10000) / 10000) * 100
rendement_spy = ((spy_curve[-1] - 10000) / 10000) * 100
alpha = rendement_bot - rendement_spy

print("\n🏆 --- VERDICT FINAL ---")
print(f"🤖 Rendement BOT     : {rendement_bot:.2f}%")
print(f"🇺🇸 Rendement S&P 500 : {rendement_spy:.2f}%")
print(f"🚀 ALPHA (Surperf.)  : {alpha:.2f}%")
print("------------------------")