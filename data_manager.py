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
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            tables = pd.read_html(io.StringIO(response.text))
            tickers = tables[0]['Symbol'].head(100).tolist()
            return [t.replace('.', '-') for t in tickers]
        except:
            return []

    def update_historical_data(self, tickers: list, start_date: str, end_date: str):
        print(f"📥 Vérification des données ({start_date} à {end_date})...")

        # Yahoo Finance exclut la date de fin, donc on ajoute +1 jour
        yf_end_date = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

        for ticker in tickers:
            csv_path = os.path.join(self.data_dir, f"{ticker}_history.csv")

            do_download = True

            # 1. EST-CE QU'ON A DÉJÀ LES BONNES DONNÉES ?
            if os.path.exists(csv_path):
                try:
                    # Remplace la ligne 39 par celle-ci :
                    df_test = pd.read_csv(csv_path, index_col=0, parse_dates=True, date_format='%Y-%m-%d')
                    if not df_test.empty:
                        # On récupère les dates réelles dans le fichier
                        dt_actual_start = df_test.index[0]
                        dt_req_start = datetime.strptime(start_date, '%Y-%m-%d')
                        dt_actual_end = df_test.index[-1]
                        dt_req_end = datetime.strptime(end_date, '%Y-%m-%d')

                        # Si le fichier contient TOUTE la plage demandée (ou plus), on saute le download
                        if dt_actual_start <= (dt_req_start + timedelta(days=7)) and dt_actual_end >= dt_req_end:
                            do_download = False
                except:
                    pass  # Fichier mal formé, on va redownloader

            # 2. SI BESOIN, ON TÉLÉCHARGE TOUT LE BLOC
            if do_download:
                print(f"⬇️ Récupération de {ticker}...")
                # On force multi_level_index=False pour éviter les bugs de colonnes imbriquées
                df = yf.download(ticker, start=start_date, end=yf_end_date, progress=False, multi_level_index=False)

                if not df.empty:
                    # On ne garde que la colonne 'Close'
                    df_to_save = df[['Close']]
                    df_to_save.to_csv(csv_path)
                else:
                    print(f"⚠️ Aucune donnée pour {ticker}")

        print("✅ Base de données synchronisée.")