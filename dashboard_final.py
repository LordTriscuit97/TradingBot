import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(layout="wide", page_title="Simulateur 2025 Fast")
st.title("🚀 Simulation Journalière 2025 (Optimisée)")

# --- 1. PARAMÈTRES (Entrée Hebdo -> Conversion Daily) ---
st.sidebar.header("Paramètres (Issus de l'Optimiseur)")
k_hebdo = st.sidebar.number_input("Kalman Seuil (Hebdo)", 0.01, 0.50, 0.15)
z_fen_hebdo = st.sidebar.number_input("Z-Score Fenêtre (Hebdo)", 4, 52, 8)
z_seuil = st.sidebar.number_input("Z-Score Seuil", 1.0, 4.0, 2.0)
b_fen_hebdo = st.sidebar.number_input("Breakout Fenêtre (Hebdo)", 4, 52, 12)

# CONVERSION AUTOMATIQUE
k_daily = k_hebdo / 5.0
z_fen_daily = int(z_fen_hebdo * 5)
b_fen_daily = int(b_fen_hebdo * 5)

st.sidebar.markdown("---")
st.sidebar.caption(f"🔧 Conversion Daily : Kalman={k_daily:.3f} | Z-Score={z_fen_daily}j | Breakout={b_fen_daily}j")

# --- 2. DONNÉES 2025 ---
TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'LLY', 'AVGO',
    'JPM', 'XOM', 'UNH', 'V', 'PG', 'MA', 'JNJ', 'HD', 'MRK', 'COST'
]

if st.sidebar.button("LANCER SIMULATION 2025"):
    with st.spinner("Calcul en cours..."):
        # Téléchargement : On prend depuis mi-2024 pour avoir de l'élan (Warm-up)
        data = yf.download(TICKERS, start="2024-06-01", group_by='ticker', progress=False)

        # --- PRÉ-CALCUL DES SIGNAUX (VECTORIEL) ---
        # Au lieu de calculer jour par jour dans la boucle, on calcule tout AVANT.
        # C'est 100x plus rapide.

        signals_kalman = pd.DataFrame(index=data.index, columns=TICKERS).fillna(0)
        signals_zscore = pd.DataFrame(index=data.index, columns=TICKERS).fillna(0)
        signals_breakout = pd.DataFrame(index=data.index, columns=TICKERS).fillna(0)
        prices = pd.DataFrame(index=data.index, columns=TICKERS)

        for t in TICKERS:
            try:
                # Gestion MultiIndex safe
                try:
                    p = data[t]['Close']
                except:
                    p = data.xs(t, level=0, axis=1)['Close']
                p = p.fillna(method='ffill')
                prices[t] = p

                # 1. KALMAN
                kf = KalmanFilter(transition_matrices=[1], observation_matrices=[1],
                                  initial_state_mean=p.iloc[0], initial_state_covariance=1,
                                  observation_covariance=1, transition_covariance=0.01)
                means, _ = kf.filter(p.values)
                pente = pd.Series(means.flatten(), index=p.index).diff()
                signals_kalman[t] = np.where(pente > k_daily, 1, np.where(pente < -k_daily, -1, 0))

                # 2. Z-SCORE
                rm = p.rolling(z_fen_daily).mean()
                rstd = p.rolling(z_fen_daily).std()
                z = (p - rm) / rstd
                signals_zscore[t] = np.where(z < -z_seuil, 1, np.where(z > z_seuil, -1, 0))

                # 3. BREAKOUT
                rmax = p.rolling(b_fen_daily).max().shift(1)  # Max d'hier
                rmin = p.rolling(b_fen_daily).min().shift(1)  # Min d'hier
                signals_breakout[t] = np.where(p > rmax, 1, np.where(p < rmin, -1, 0))

            except:
                continue

        # --- BOUCLE DE TRADING (RAPIDE) ---
        # On ne garde que les dates de 2025
        dates_2025 = [d for d in data.index if d.year >= 2025]

        # Portefeuilles
        cash = {"Kalman": 10000.0, "Z-Score": 10000.0, "Breakout": 10000.0}
        pos = {"Kalman": {}, "Z-Score": {}, "Breakout": {}}
        history = []

        prog = st.progress(0)

        for i, date in enumerate(dates_2025):
            if i % 10 == 0: prog.progress(i / len(dates_2025))

            valeur_jour = {}
            current_prices = prices.loc[date]

            # Application des 3 stratégies
            for strat_name, signals_df in [("Kalman", signals_kalman), ("Z-Score", signals_zscore),
                                           ("Breakout", signals_breakout)]:

                # Valeur du portefeuille
                val = cash[strat_name]
                for t, q in pos[strat_name].items():
                    val += q * current_prices[t]
                valeur_jour[strat_name] = val

                # Trading
                for t in TICKERS:
                    sig = signals_df.at[date, t]
                    p = current_prices[t]

                    if pd.isna(p): continue

                    mise = 1000.0

                    # ACHAT
                    if sig == 1 and cash[strat_name] >= mise and t not in pos[strat_name]:
                        qte = mise / p
                        pos[strat_name][t] = qte
                        cash[strat_name] -= mise

                    # VENTE
                    elif sig == -1 and t in pos[strat_name]:
                        qte = pos[strat_name][t]
                        cash[strat_name] += qte * p
                        del pos[strat_name][t]

            valeur_jour['date'] = date
            history.append(valeur_jour)

        prog.progress(100)

        # --- RÉSULTATS ---
        df_res = pd.DataFrame(history).set_index('date')

        # Affichage
        st.success("Simulation Terminée !")
        st.line_chart(df_res)

        cols = st.columns(3)
        for i, strat in enumerate(["Kalman", "Z-Score", "Breakout"]):
            perf = ((df_res[strat].iloc[-1] - 10000) / 10000) * 100
            cols[i].metric(strat, f"{perf:.2f}%")

        st.write("Dernières positions (Breakout):", pos["Breakout"])