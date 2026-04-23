import yfinance as yf


def get_stock_data(symbol, start_date, end_date):
    """
    Télécharge les données boursières pour un symbole donné.
    :param symbol: Le ticker (ex: 'AAPL' pour Apple)
    :param start_date: Date de début (ex: '2023-01-01')
    :param end_date: Date de fin (ex: '2024-01-01')
    :return: Un DataFrame Pandas contenant les prix
    """
    print(f"📥 Téléchargement des données pour {symbol}...")

    # On télécharge les données journalières
    data = yf.download(symbol, start=start_date, end=end_date, progress=False)

    # On garde seulement la colonne 'Close' (Prix de fermeture) pour simplifier
    # C'est souvent suffisant pour nos algos
    return data[['Close']]