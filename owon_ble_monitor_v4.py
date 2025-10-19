"""
OWON 16 BLE Monitor – Version modulaire 3.1 pour Raspberry Pi 5

Ce module permet :
- de surveiller un multimètre OWON 16 via BLE,
- d'annoncer vocalement les changements de fonction mesurée,
- d'être utilisé soit en mode autonome, soit intégré dans un gestionnaire,
- de charger ses paramètres vocaux depuis un fichier JSON.

Auteurs
-------
Open Source
"""

__version__ = "3.1"
__date__ = "2025-04-28"

import asyncio
import json
import threading
from datetime import datetime
from typing import Optional

import pyttsx3
from bleak import BleakClient, BleakScanner, BLEDevice

from owon_decoder import Owon_MultimeterData  # Module de décodage

# Configuration BLE
MODEL_NAME = "BDM"  # Nom BLE du multimètre
CHARACTERISTIC_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"  # UUID des mesures
CONFIG_FILE = "owon_monitor_parameters.json"  # Fichier de paramètres TTS

# Initialisation de la synthèse vocale
tts = pyttsx3.init()


def load_tts_parameters(filename: str) -> None:
    """
    Charge les paramètres TTS depuis un fichier JSON.

    Si un paramètre est manquant ou invalide, une valeur par défaut est utilisée.

    Parameters
    ----------
    filename : str
        Chemin du fichier JSON contenant les paramètres vocaux.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            params = json.load(f)

        # Configuration du débit de parole ("rate") avec secours à 120 mots/minute
        tts.setProperty("rate", params.get("rate", 120))

        # Configuration du volume sonore ("volume") avec secours à 0.8 (80 %)
        tts.setProperty("volume", params.get("volume", 0.8))

        # Tentative de sélection de la langue
        lang = params.get("language", "fr").lower()
        found = False
        for voice in tts.getProperty("voices"):
            if lang in voice.id.lower() or (voice.languages and lang in voice.languages[0].decode().lower()):
                tts.setProperty("voice", voice.id)
                found = True
                break

        # Si aucune voix trouvée, forcer "french" pour espeak sur Raspberry Pi
        if not found and lang == "fr":
            tts.setProperty("voice", "french")

    except Exception as e:
        print(f"[⚠️] Erreur de chargement des paramètres TTS : {e}")


# Charger les paramètres TTS au lancement
load_tts_parameters(CONFIG_FILE)


class OwonBLEMonitor:
    """
    Surveillance du multimètre OWON 16 via BLE.

    Attributes
    ----------
    last_unit : Optional[str]
        Dernière unité de mesure détectée.
    last_data : Optional[Owon_MultimeterData]
        Dernières données décodées.
    client : Optional[BleakClient]
        Client BLE actif.
    running : bool
        Indique si la surveillance est active.
    thread : Optional[threading.Thread]
        Thread d'exécution.
    """

    def __init__(self) -> None:
        """Initialisation du monitor BLE."""
        self.last_unit: Optional[str] = None
        self.last_data: Optional[Owon_MultimeterData] = None
        self.client: Optional[BleakClient] = None
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None

    def announce(self, text: str) -> None:
        """
        Annonce vocalement un message.

        Parameters
        ----------
        text : str
            Message à annoncer.
        """
        print(f"[🗣] {text}")
        tts.say(text)
        tts.runAndWait()

    def handle_notification(self, handle: int, data: bytearray) -> None:
        """
        Callback sur réception d'une trame BLE.

        Parameters
        ----------
        handle : int
            Identifiant de la caractéristique BLE.
        data : bytearray
            Données brutes reçues.
        """
        try:
            raw = list(data)
            decoded = Owon_MultimeterData(raw)
            self.last_data = decoded

            if decoded.unit_name != self.last_unit:
                self.last_unit = decoded.unit_name
                if decoded.unit_name == "unknown":
                    msg = f"Mode inconnu, code unité {decoded.unit}"
                else:
                    msg = f"{decoded.unit_name}, {decoded.value}"

                print(f"[{datetime.now().isoformat()}] ➤ {msg}")
                self.announce(msg)

        except Exception as e:
            print(f"[⚠️] Erreur de décodage : {e}")

    async def wait_for_device(self) -> BLEDevice:
        """
        Recherche du multimètre OWON 16.

        Returns
        -------
        BLEDevice
            Périphérique BLE trouvé.
        """
        self.announce("En attente de connexion au multimètre OWON 16. Activez le Bluetooth.")
        while True:
            devices = await BleakScanner.discover(timeout=4.0)
            for dev in devices:
                if (dev.name or "").strip().upper() == MODEL_NAME:
                    print(f"✅ OWON détecté : {dev.name} @ {dev.address}")
                    self.announce("Multimètre OWON détecté. Connexion.")
                    return dev
            await asyncio.sleep(2)

    async def run(self) -> None:
        """
        Boucle principale d'acquisition et d'annonces.
        """
        device = await self.wait_for_device()

        try:
            async with BleakClient(device) as client:
                self.client = client
                await client.start_notify(CHARACTERISTIC_UUID, self.handle_notification)
                self.announce("Lecture des mesures en cours.")
                print("=> Connexion active. Appuyez sur Ctrl+C pour quitter.")
                self.running = True
                while self.running:
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"[❌] Erreur de connexion : {e}")
            self.announce("Erreur de connexion.")

        finally:
            if self.client:
                await self.client.disconnect()
                print("🔌 Déconnecté.")
                self.announce("Déconnexion du multimètre OWON.")

    def start(self) -> None:
        """Démarre la surveillance dans un thread."""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._run_async)
            self.thread.start()

    def _run_async(self) -> None:
        """Lance l'event loop asyncio."""
        asyncio.run(self.run())

    def stop(self) -> None:
        """Demande l'arrêt du monitoring BLE."""
        self.running = False


if __name__ == "__main__":
    # Mode autonome console
    monitor = OwonBLEMonitor()
    try:
        monitor.start()
        while True:
            pass  # Boucle principale jusqu'à Ctrl+C
    except KeyboardInterrupt:
        print("\n⏹ Arrêt demandé par l'utilisateur.")
        monitor.stop()
        tts.say("Arrêt du script")
        tts.runAndWait()
