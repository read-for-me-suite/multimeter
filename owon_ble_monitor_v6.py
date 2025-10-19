"""
OWON 16 BLE Monitor – Version 6.4 pour Raspberry Pi 5

Ce module permet :
- de surveiller un multimètre OWON 16 via BLE,
- d'annoncer vocalement uniquement lors d'un changement réel de mesure,
- d'annoncer aussi les changements d'états (Hold, Relative, AutoRange),
- d'attendre un délai configurable avant annonce,
- d'enregistrer les données dans un fichier CSV (réinitialisé à chaque lancement),
- d'afficher les données en console uniquement lors d'un changement.

Auteurs
-------
Open Source, adapté pour architecture modulaire
"""

__version__ = "6.4"
__date__ = "2025-04-29"

import asyncio
import json
import threading
import time
import csv
from datetime import datetime
from typing import Optional, Dict, List

import pyttsx3
from bleak import BleakClient, BleakScanner, BLEDevice

from owon_decoder import Owon_MultimeterData

# === Configuration générale ===

MODEL_NAME = "BDM"
CHARACTERISTIC_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"
CONFIG_FILE = "owon_monitor_parameters.json"

# === Configuration fonctionnelle ===

ENABLE_LOGGING = True
LOG_FILE_NAME = "owon_multimeter_log.csv"  # ATTENTION : fichier écrasé à chaque lancement
ANNOUNCE_DELAY_SEC = 1.5  # Délai avant annonce d'une nouvelle mesure stable

# === Initialisation synthèse vocale ===

tts = pyttsx3.init()

def force_default_voice(default_lang: str = "en-gb") -> None:
    """Force une voix par défaut si disponible."""
    voices = tts.getProperty("voices")
    for voice in voices:
        langs = [lang.decode() if isinstance(lang, bytes) else lang for lang in voice.languages]
        if any(default_lang in l.lower() for l in langs):
            tts.setProperty("voice", voice.id)
            print(f"[INFO] Voix par défaut sélectionnée : {voice.name} ({voice.id})")
            return
    print("[⚠️] Voix par défaut non trouvée, utilisation de la voix système.")

def load_tts_parameters(filename: str) -> None:
    """Charge les paramètres TTS depuis un fichier JSON."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            params = json.load(f)
        tts.setProperty("rate", params.get("rate", 120))
        tts.setProperty("volume", params.get("volume", 0.8))
        lang = params.get("language", "fr-fr").lower()
        voices = tts.getProperty("voices")
        for voice in voices:
            langs = [lang.decode() if isinstance(lang, bytes) else lang for lang in voice.languages]
            if any(lang in l.lower() for l in langs):
                tts.setProperty("voice", voice.id)
                print(f"[INFO] Voix {voice.name} sélectionnée pour {lang}")
                return
        print(f"[⚠️] Voix pour {lang} non trouvée, conservation de la voix actuelle.")
    except Exception as e:
        print(f"[⚠️] Erreur de chargement des paramètres TTS : {e}")

force_default_voice("en-gb")
load_tts_parameters(CONFIG_FILE)


class OwonBLEMonitor:
    """Surveillance BLE du multimètre OWON 16."""

    def __init__(self) -> None:
        """Initialisation."""
        self.last_data: Optional[Owon_MultimeterData] = None
        self.last_raw_data: Optional[List[int]] = None
        self.last_announced_raw_data: Optional[List[int]] = None
        self.last_change_time: float = time.time()
        self.last_hold = 0
        self.last_relative = 0
        self.last_autorange = 0
        self.client: Optional[BleakClient] = None
        self.running: bool = False
        self.connected: bool = False
        self.thread: Optional[threading.Thread] = None

        if ENABLE_LOGGING:
            self.init_csv_log()

    def init_csv_log(self) -> None:
        """Initialise le fichier CSV (écrase l'ancien)."""
        with open(LOG_FILE_NAME, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerow([
                "timestamp", "raw_data", "overflow",
                "data_hold_mode", "relative_mode", "auto_ranging",
                "low_battery", "value", "unit_name"
            ])
        print(f"[INFO] Fichier de log {LOG_FILE_NAME} initialisé.")

    def log_to_csv(self, data: Owon_MultimeterData) -> None:
        """Ajoute une ligne au fichier CSV."""
        if not ENABLE_LOGGING:
            return
        with open(LOG_FILE_NAME, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerow([
                datetime.now().isoformat(),
                " ".join(str(b) for b in data.raw_data),
                data.flag_status_to_string(data.overflow),
                data.flag_status_to_string(data.data_hold_mode),
                data.flag_status_to_string(data.relative_mode),
                data.flag_status_to_string(data.auto_ranging),
                data.flag_status_to_string(data.low_battery),
                data.value,
                data.unit_name
            ])

    def announce(self, text: str) -> None:
        """Annonce vocalement un message."""
        print(f"[🗣] {text}")
        tts.say(text)
        tts.runAndWait()

    def handle_notification(self, handle: int, data: bytearray) -> None:
        """Callback appelée pour chaque trame BLE reçue."""
        try:
            decoded = Owon_MultimeterData(list(data))
            now = time.time()

            if self.last_raw_data != decoded.raw_data:
                self.last_raw_data = decoded.raw_data
                self.last_change_time = now
                self.last_data = decoded

                print(decoded)
                self.log_to_csv(decoded)

                if decoded.data_hold_mode != self.last_hold:
                    mode = "activé" if decoded.data_hold_mode else "désactivé"
                    self.announce(f"Mode Hold {mode}")
                    self.last_hold = decoded.data_hold_mode

                if decoded.relative_mode != self.last_relative:
                    mode = "activé" if decoded.relative_mode else "désactivé"
                    self.announce(f"Mode Relatif {mode}")
                    self.last_relative = decoded.relative_mode

                if decoded.auto_ranging != self.last_autorange:
                    mode = "activé" if decoded.auto_ranging else "désactivé"
                    self.announce(f"Mode AutoRange {mode}")
                    self.last_autorange = decoded.auto_ranging

            if (self.last_data and
                self.last_announced_raw_data != self.last_raw_data and
                now - self.last_change_time >= ANNOUNCE_DELAY_SEC):
                autorange_text = "AutoRange activé" if self.last_data.auto_ranging else "AutoRange désactivé"
                message = f"{self.last_data.value} {self.last_data.unit_name}, {autorange_text}"
                self.announce(message)
                self.last_announced_raw_data = list(self.last_raw_data)

        except Exception as e:
            print(f"[⚠️] Erreur de décodage : {e}")

    def get_measure(self) -> Dict[str, Optional[str]]:
        """
        Retourne la dernière mesure décodée.

        Returns
        -------
        dict
            {"value": float, "unit": str, "autorange": str}
        """
        if self.last_data:
            autorange_text = "AutoRange activé" if self.last_data.auto_ranging else "AutoRange désactivé"
            return {
                "value": self.last_data.value,
                "unit": self.last_data.unit_name,
                "autorange": autorange_text
            }
        else:
            return {
                "value": None,
                "unit": None,
                "autorange": None
            }

    def get_measure_and_say(self) -> None:
        """
        Annonce immédiatement la dernière mesure.

        Utilisé par exemple lors d'un appui bouton rotatif manuel.
        """
        if self.last_data:
            autorange_text = "AutoRange activé" if self.last_data.auto_ranging else "AutoRange désactivé"
            message = f"{self.last_data.value} {self.last_data.unit_name}, {autorange_text}"
            self.announce(message)
        else:
            self.announce("Aucune mesure disponible")

    async def wait_for_device(self) -> BLEDevice:
        """Recherche du multimètre OWON 16."""
        self.announce("En attente de connexion au multimètre OWON 16.")
        while True:
            devices = await BleakScanner.discover(timeout=4.0)
            for dev in devices:
                if (dev.name or "").strip().upper() == MODEL_NAME:
                    print(f"✅ OWON détecté : {dev.name} @ {dev.address}")
                    self.announce("Multimètre OWON détecté. Connexion.")
                    return dev
            await asyncio.sleep(2)

    async def run(self) -> None:
        """Boucle principale BLE."""
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
                await asyncio.sleep(2)

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
    monitor = OwonBLEMonitor()
    try:
        monitor.start()
        while True:
            pass
    except KeyboardInterrupt:
        print("\n⏹ Arrêt demandé par l'utilisateur.")
        monitor.stop()
        tts.say("Arrêt du script")
        tts.runAndWait()
