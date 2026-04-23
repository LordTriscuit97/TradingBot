import json
import os


class SubPortfolio:
    """Représente un compte unique pour une stratégie spécifique."""

    def __init__(self, nom, cash_initial):
        self.nom = nom
        self.cash = float(cash_initial)
        self.actions = {}  # ex: {'AAPL': 10, 'MSFT': 5}
        self.valeur_historique = []  # Pour tracer la courbe à la fin

    def acheter(self, symbol, prix, quantite):
        cout = prix * quantite
        if cout <= self.cash:
            self.cash -= cout
            if symbol in self.actions:
                self.actions[symbol] += quantite
            else:
                self.actions[symbol] = quantite
            return True
        return False

    def vendre(self, symbol, prix, quantite):
        if symbol in self.actions and self.actions[symbol] >= quantite:
            gain = prix * quantite
            self.cash += gain
            self.actions[symbol] -= quantite
            # Nettoyage si quantité nulle
            if self.actions[symbol] <= 0:
                del self.actions[symbol]
            return True
        return False

    def get_valeur_totale(self, prix_actuels):
        """
        Calcule la valeur totale (Cash + Actions)
        :param prix_actuels: Dictionnaire { 'AAPL': 150.0, 'MSFT': 250.0 }
        """
        valeur_actions = 0
        for symbol, qte in self.actions.items():
            # Si on a le prix du jour, on valorise, sinon on ignore (prudence)
            if symbol in prix_actuels:
                valeur_actions += qte * prix_actuels[symbol]
        return self.cash + valeur_actions


class MasterPortfolio:
    """Le Gestionnaire qui supervise les 4 stratégies."""

    def __init__(self, cash_par_strategie=10000.0):
        # On crée les 4 comptes séparés
        self.comptes = {
            "Kalman": SubPortfolio("Kalman", cash_par_strategie),
            "Z-Score": SubPortfolio("Z-Score", cash_par_strategie),
            "Breakout": SubPortfolio("Breakout", cash_par_strategie),
            "Benchmark_SP500": SubPortfolio("Buy & Hold", cash_par_strategie)
        }
        self.fichier_sauvegarde = "master_portfolio.json"

    def sauvegarder(self):
        # On transforme tout en format JSON compatible
        donnees_globales = {}
        for nom, compte in self.comptes.items():
            donnees_globales[nom] = {
                "cash": compte.cash,
                "actions": compte.actions,
                "historique": compte.valeur_historique
            }

        with open(self.fichier_sauvegarde, 'w') as f:
            json.dump(donnees_globales, f)
        print("💾 État des 4 portefeuilles sauvegardé.")

    def charger(self):
        if os.path.exists(self.fichier_sauvegarde):
            with open(self.fichier_sauvegarde, 'r') as f:
                donnees = json.load(f)

            for nom, data in donnees.items():
                if nom in self.comptes:
                    self.comptes[nom].cash = data["cash"]
                    self.comptes[nom].actions = data["actions"]
                    self.comptes[nom].valeur_historique = data.get("historique", [])
            print("📂 Mémoire rechargée pour les 4 stratégies.")
        else:
            print("⚠️ Aucune sauvegarde. Démarrage à neuf.")