import pandas as pd
import yfinance as yf
from tqdm import tqdm  # Barre de progression pour voir que ça avance
from portfolio import MasterPortfolio
from data_manager import DataManager
from datetime import datetime
import os

# --- 1. CONFIGURATION DE L'UNIVERS ---
# On commence avec 10 actions "Stars" pour valider la vitesse
UNIVERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC']
BENCHMARK = 'SPY'  # Le ticker pour le S&P 500

# Paramètres de simulation
DATE_DEBUT = '2023-01-01'
DATE_FIN = '2024-01-01'
CASH_INITIAL = 10000.0

# 1. Configuration des paramètres de test
FMP_API_KEY = "METS_TA_CLE_ICI" # Laisse ça tel quel si tu n'en as pas encore
START_DATE = "2025-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')


def telecharger_tout(tickers):
    """Télécharge tout d'un coup pour éviter la lenteur dans la boucle."""
    print("📥 Téléchargement des données de marché...")
    # On ajoute le SPY à la liste pour le télécharger aussi
    tous_tickers = tickers + [BENCHMARK]

    # On télécharge en bloc (plus rapide)
    data = yf.download(tous_tickers, start=DATE_DEBUT, end=DATE_FIN, group_by='ticker', progress=True)
    return data


def run_simulation():
    # 1. PRÉPARATION
    data_market = telecharger_tout(UNIVERS)

    # Initialisation des cerveaux
    strategies = [

    ]

    # Initialisation des comptes (3 stratégies + 1 Benchmark)
    master = MasterPortfolio(cash_par_strategie=CASH_INITIAL)

    # On récupère la liste des jours de bourse (basé sur SPY car il est toujours là)
    # yfinance renvoie parfois un MultiIndex, on s'assure d'avoir les dates
    try:
        jours_de_bourse = data_market[BENCHMARK].index
    except:
        # Fallback si structure différente
        jours_de_bourse = data_market.index

    print(f"🔄 Démarrage de la simulation sur {len(jours_de_bourse)} jours...")

    # 2. BOUCLE TEMPORELLE (WALK-FORWARD)
    # On utilise tqdm pour afficher une belle barre de chargement
    for i in tqdm(range(30, len(jours_de_bourse))):

        date_du_jour = jours_de_bourse[i]

        # --- A. GESTION DU BENCHMARK (BUY & HOLD SP500) ---
        # Au premier jour de la boucle, on achète tout ce qu'on peut de SPY
        compte_benchmark = master.comptes["Benchmark_SP500"]
        if compte_benchmark.cash > 200:  # S'il reste du cash
            try:
                # Récupérer le prix du SPY ce jour-là.
                # .loc permet d'accéder par la date, ['Close'] donne le prix
                # On gère le cas où les données sont à plusieurs niveaux (MultiIndex)
                try:
                    prix_spy = float(data_market[BENCHMARK].loc[date_du_jour]['Close'])
                except:
                    # Si format simple
                    prix_spy = float(data_market['Close'][BENCHMARK].loc[date_du_jour])

                qte = (compte_benchmark.cash - 1) / prix_spy
                compte_benchmark.acheter(BENCHMARK, prix_spy, qte)
            except Exception as e:
                pass  # Parfois données manquantes pour un jour précis

        # --- B. GESTION DES STRATÉGIES ACTIVES ---

        # On extrait les données connues JUSQU'À HIER (Simulation réaliste : on ne voit pas le futur)
        # i représente aujourd'hui, donc :i c'est du début jusqu'à hier

        # Pour chaque action de l'univers
        for symbol in UNIVERS:
            try:
                # Extraction propre des données de l'action
                try:
                    df_symbol = data_market[symbol].iloc[:i]  # Historique connu
                    prix_actuel = float(data_market[symbol].loc[date_du_jour]['Close'])
                except:
                    # Si structure différente (parfois yfinance change)
                    df_symbol = data_market.xs(symbol, level=0, axis=1).iloc[:i]
                    prix_actuel = float(df_symbol['Close'].iloc[-1])

                # On demande l'avis de chaque stratège
                for strat in strategies:
                    nom_strat = strat.name
                    # Note: on mappe les noms techniques aux noms des comptes dans portfolio.py
                    if "Kalman" in nom_strat:
                        nom_compte = "Kalman"
                    elif "Z-Score" in nom_strat:
                        nom_compte = "Z-Score"
                    elif "Breakout" in nom_strat:
                        nom_compte = "Breakout"

                    compte = master.comptes[nom_compte]
                    decision = strat.analyser(df_symbol['Close'])

                    # EXÉCUTION
                    # Règle de gestion : On investit 10% du capital initial par ligne (1000$)
                    mise_fixe = 1000.0

                    if decision == 1:  # ACHAT
                        if symbol not in compte.actions:  # On évite de cumuler pour simplifier
                            if compte.cash >= mise_fixe:
                                qte = mise_fixe / prix_actuel
                                compte.acheter(symbol, prix_actuel, qte)

                    elif decision == -1:  # VENTE
                        if symbol in compte.actions:
                            qte = compte.actions[symbol]  # On vend tout
                            compte.vendre(symbol, prix_actuel, qte)

            except Exception as e:
                # Si une donnée manque pour une action ce jour-là, on saute
                continue

        # --- C. MISE À JOUR DES VALEURS DU PORTEFEUILLE ---
        dico_prix_du_jour = {}
        for sym in UNIVERS + [BENCHMARK]:
            try:
                try:
                    p = float(data_market[sym].loc[date_du_jour]['Close'])
                except:
                    p = float(data_market['Close'][sym].loc[date_du_jour])
                dico_prix_du_jour[sym] = p
            except:
                pass

        for compte in master.comptes.values():
            valeur_totale = compte.get_valeur_totale(dico_prix_du_jour)

            # --- CORRECTION ICI : On convertit la date en texte (String) ---
            date_texte = date_du_jour.strftime('%Y-%m-%d')

            compte.valeur_historique.append({
                'date': date_texte,
                'valeur': valeur_totale
            })

    # 3. FIN & SAUVEGARDE
    master.sauvegarder()
    print("\n✅ Simulation terminée. Résultats sauvegardés.")


if __name__ == "__main__":
    manager = DataManager()
    top_100 = manager.get_top_100_tickers()

    if top_100:
        manager.update_historical_data(top_100, START_DATE, END_DATE)

