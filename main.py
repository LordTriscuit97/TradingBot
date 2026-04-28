import pandas as pd
import yfinance as yf
from tqdm import tqdm  # Barre de progression pour voir que ça avance
from portfolio import Portfolio
from data_manager import DataManager
from datetime import datetime
import os



START_DATE = "2025-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')



if __name__ == "__main__":
    manager = DataManager()
    top_100 = manager.get_top_100_tickers()

    if top_100:
        manager.update_historical_data(top_100, START_DATE, END_DATE)


