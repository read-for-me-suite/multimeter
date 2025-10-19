"""
OWON 16 BLE Monitor – Version modulaire 5.1 pour Raspberry Pi 5

Ce module permet :
- de surveiller un multimètre OWON 16 via BLE,
- d'annoncer vocalement les changements de fonction, de mode et de valeur mesurée,
- de détecter et annoncer toute déconnexion du multimètre,
- de gérer proprement les voix TTS au démarrage et depuis un fichier JSON.

Auteurs
-------
Open Source, adapté pour architecture modulaire
"""

__version__ = "5.1"
__date__ = "2025-04-28"

import asyncio
import json
import threading
from datetime import datetime
from typing import Optional, Dict

import pyttsx3
from bleak import BleakClient, BleakScanner, BLEDevice

from owon_decoder import Owon_MultimeterData  # Module de décodage

# Configuration BLE
MODEL_NAME = "BDM"  # Nom BLE du multimètre
CHARACTERISTIC_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"  # UUID des mesures
CONFIG_FILE = "owon_monitor_parameters.json"  # Fichier JSON des paramètres vocaux

# Initialisation de la synthèse vocale
tts = pyttsx3.init()


def force_default_voice(default_lang: str = "en-gb") -> None:
    """
    Force l'utilisation d'une voix par défaut au démarrage.

    Parameters
    ----------
    default_lang : str
        Code langue par défaut à utiliser (ex: 'en-gb' pour anglais UK).
    """
    voices = tts.getProperty("voices")
    for voice in voices:
        langs = [lang.decode() if isinstance(lang, bytes) else lang for lang in voice.languages]
        if any(default_lang in l.lower() for l in langs):
            tts.setProperty("voice", voice.id)
            print(f"[INFO] Voix par défaut sélectionnée : {voice.name} ({voice.id})")
            return
    print("[⚠️] Voix par défaut non trouvée, utilisation de la voix système.")


def load_tts_parameters(filename: str) -> None:
    """
    Charge les paramètres TTS depuis un fichier JSON.

    Parameters
    ----------
    filename : str
        Chemin du fichier JSON contenant les paramètres vocaux.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            params = json.load(f)

        tts.setProperty("rate", params.get("rate", 120))
        tts.setProperty("volume", params.get("volume", 0.8))

        lang = params.get("language", "fr-fr").lower()
        found = False
        voices = tts.getProperty("voices")
        for voice in voices:
            langs = [lang.decode() if isinstance(lang, bytes) else lang for lang in voice.languages]
            if any(lang in l.lower() for l in langs):
                tts.setProperty("voice", voice.id)
                found = True
                print(f"[INFO] Voix {voice.name} sélectionnée pour la langue {lang}")
                break

        if not found:
            print(f"[⚠️] Voix pour la langue {lang} non trouvée, conservation de la voix actuelle.")

    except Exception as e:
        print(f"[⚠️] Erreur de chargement des paramètres TTS : {e}")


# Appliquer la voix par défaut + charger la configuration utilisateur
force_default_voice("en-gb")
load_tts_parameters(CONFIG_FILE)


class OwonBLEMonitor:
    """
    Surveillance du multimètre OWON 16 via BLE.

    Attributes
    ----------
    last_data : Optional[Owon_MultimeterData]
        Dernières données décodées.
    client : Optional[BleakClient]
        Client BLE actif.
    running : bool
        Indique si la surveillance est active.
    connected : bool
        Indique si la connexion BLE est actuellement active.
    thread : Optional[threading.Thread]
        Thread d'exécution.
    """

    def __init__(self) -> None:
        """Initialisation du monitor BLE."""
        self.last_data: Optional[Owon_MultimeterData] = None
        self.client: Optional[BleakClient] = None
        self.running: bool = False
        self.connected: bool = False
        self.thread: Optional[threading.Thread] = None

        # Mémoire pour détecter les changements d'état
        self.last_hold = 0
        self.last_relative = 0
        self.last_autorange = 0
        self.last_unit_name = ""

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
            decoded = Owon_MultimeterData(list(data))
            self.last_data = decoded

            messages = []

            # Détection des changements de mode
            if decoded.data_hold_mode != self.last_hold:
                mode = "activé" if decoded.data_hold_mode else "désactivé"
                messages.append(f"Mode Hold {mode}")
                self.last_hold = decoded.data_hold_mode

            if decoded.relative_mode != self.last_relative:
                mode = "activé" if decoded.relative_mode else "désactivé"
                messages.append(f"Mode Relatif {mode}")
                self.last_relative = decoded.relative_mode

            if decoded.auto_ranging != self.last_autorange:
                mode = "activé" if decoded.auto_ranging else "désactivé"
                messages.append(f"Mode AutoRange {mode}")
                self.last_autorange = decoded.auto_ranging

            # Détection du changement d'unité
            if decoded.unit_name != self.last_unit_name:
                self.last_unit_name = decoded.unit_name
                messages.append(f"{decoded.value} {decoded.unit_name}")

            # Annoncer tous les messages accumulés
            for msg in messages:
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
                    print(f"OWON détecté : {dev.name} @ {dev.address}")
                    self.announce("Multimètre OWON détecté. Connexion.")
                    return dev
            await asyncio.sleep(2)

    async def run(self) -> None:
        """
        Boucle principale d'acquisition et de surveillance.
        """
        while self.running:
            try:
                device = await self.wait_for_device()
                async with BleakClient(device) as client:
                    self.client = client
                    self.connected = True

                    await client.start_notify(CHARACTERISTIC_UUID, self.handle_notification)
                    self.announce("Lecture des mesures en cours.")

                    while self.running and client.is_connected:
                        await asyncio.sleep(1)

                    if not client.is_connected:
                        self.connected = False
                        self.announce("Multimètre déconnecté.")

            except Exception as e:
                print(f"[⚠️] Erreur BLE : {e}")
                self.connected = False
                await asyncio.sleep(2)  # Attente avant tentative de reconnexion

    def get_measure(self) -> Dict[str, Optional[float]]:
        """
        Retourne la mesure actuelle sous forme de dictionnaire.

        Returns
        -------
        dict
            {"value": float, "unit": str}
        """
        if self.last_data:
            return {"value": self.last_data.value, "unit": self.last_data.unit_name}
        else:
            return {"value": None, "unit": None}

    def get_measure_and_say(self) -> None:
        """
        Annonce vocalement la mesure actuelle.
        """
        if self.last_data:
            message = f"{self.last_data.value} {self.last_data.unit_name}"
            self.announce(message)

    def start(self) -> None:
        """Démarre la surveillance dans un thread."""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._run_async)
            self.thread.start()

    def _run_async(self) -> None:
        """Lance la boucle asyncio."""
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
