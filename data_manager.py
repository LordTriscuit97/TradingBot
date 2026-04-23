import os
import io
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta


class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def get_top_100_tickers(self) -> list:
        print("Scraping Wikipedia...")
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"Échec de la connexion. Code: {response.status_code}")
                return []

            tables = pd.read_html(io.StringIO(response.text))
            df_sp500 = tables[0]

            tickers = df_sp500['Symbol'].head(100).tolist()
            tickers = [t.replace('.', '-') for t in tickers]
            return tickers

        except Exception as e:
            print(f"Erreur: {e}")
            return []

    def update_historical_data(self, tickers: list, start_date: str, end_date: str):
        print(f"Vérification et synchronisation des données jusqu'au {end_date}...")

        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        yf_end_date = (end_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

        for ticker in tickers:
            csv_path = os.path.join(self.data_dir, f"{ticker}_history.csv")

            if os.path.exists(csv_path):
                df_existing = pd.read_csv(csv_path, index_col='Date', parse_dates=True)

                if not df_existing.empty:
                    last_date_str = df_existing.index[-1].strftime('%Y-%m-%d')

                    if last_date_str < end_date:
                        next_day = (df_existing.index[-1] + timedelta(days=1)).strftime('%Y-%m-%d')
                        print(f"Mise à jour de {ticker}...")

                        df_new = yf.download(ticker, start=next_day, end=yf_end_date, progress=False,
                                             multi_level_index=False)

                        if not df_new.empty:
                            df_new_clean = df_new[['Close']].copy().round(4)
                            df_combined = pd.concat([df_existing, df_new_clean])
                            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
                            df_combined.to_csv(csv_path)
                    else:
                        print(f"{ticker} est déjà à jour")

                    continue

            print(f"Téléchargement initial complet pour {ticker}...")
            # On utilise yf_end_date ici aussi
            df = yf.download(ticker, start=start_date, end=yf_end_date, progress=False, multi_level_index=False)

            if not df.empty:
                df_clean = df[['Close']].copy().round(4)
                df_clean.to_csv(csv_path)
            else:
                print(f"Aucune donnée pour {ticker}.")

        print(f"Synchronisation terminée dans '{self.data_dir}/'.")