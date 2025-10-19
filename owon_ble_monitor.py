
"""
   OWON 16 BLE Monitor – Version pour Raspberry Pi 5 (console uniquement)

Ce script :
- Établit une liaison BLE avec un multimètre OWON 16 (nom Bluetooth : "BDM")
- Décode les paquets reçus (6 octets)
- Annonce vocalement toute nouvelle fonction détectée (ex : Volt DC, Ohm, °C)
- S'exécute en boucle jusqu'à interruption

⚠️ Ce script est conçu pour fonctionner uniquement sur un Raspberry Pi 5 (ou équivalent sous Linux) avec le module `bleak`.

"""

__version__ = "1.0"
__date__ = "2025-04-25"

import asyncio
import os
from bleak import BleakClient, BleakScanner, BLEDevice
import pyttsx3
from datetime import datetime
from typing import Optional
from owon_decoder import Owon_MultimeterData

# Nom BLE et UUID caractéristique du OWON 16
MODEL_NAME = "BDM"
CHARACTERISTIC_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"

# Initialisation TTS (pyttsx3 utilise espeak sur Raspberry Pi)
tts = pyttsx3.init()
tts.setProperty("rate", 150)


class OwonBLEMonitor:
    def __init__(self):
        self.last_unit: Optional[str] = None
        self.last_data: Optional[Owon_MultimeterData] = None
        self.client: Optional[BleakClient] = None

    def announce(self, text: str):
        """Annoncer un texte vocalement via la synthèse vocale (module pyttsx3)."""
        print(f"[🗣] {text}")
        tts.say(text)
        tts.runAndWait()

    def handle_notification(self, handle: int, data: bytearray):
        """Callback appelée pour chaque notification BLE (paquet reçu)"""
        try:
            raw = list(data)
            decoded = Owon_MultimeterData(raw)
            self.last_data = decoded

            if decoded.unit_name != self.last_unit:
                self.last_unit = decoded.unit_name
                msg = f"{decoded.unit_name}, {decoded.value}"
                print(f"[{datetime.now().isoformat()}] ➤ {msg}")
                self.announce(msg)

        except Exception as e:
            print(f"[⚠️] Erreur de décodage : {e}")

    async def wait_for_device(self) -> BLEDevice:
        """Boucle de détection du OWON 16 jusqu'à sa découverte"""
        self.announce("En attente de connexion au multimètre OWON 16. Activez le Bluetooth.")
        while True:
            devices = await BleakScanner.discover(timeout=4.0)
            for dev in devices:
                if (dev.name or "").strip().upper() == MODEL_NAME:
                    print(f"✅ OWON détecté : {dev.name} @ {dev.address}")
                    self.announce("Multimètre OWON détecté. Connexion.")
                    return dev
            await asyncio.sleep(2)

    async def run(self):
        """Boucle principale : connexion, réception et lecture"""
        device = await self.wait_for_device()

        try:
            async with BleakClient(device) as client:
                self.client = client
                await client.start_notify(CHARACTERISTIC_UUID, self.handle_notification)
                self.announce("Lecture des mesures en cours.")
                print("=> Connexion active. Appuyez sur Ctrl+C pour quitter.")
                while True:
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"[❌] Erreur de connexion : {e}")
            self.announce("Erreur de connexion.")

        finally:
            if self.client:
                await self.client.disconnect()
                print("🔌 Déconnecté.")
                self.announce("Déconnexion du multimètre OWON.")


if __name__ == "__main__":
    try:
        asyncio.run(OwonBLEMonitor().run())
    except KeyboardInterrupt:
        print("\n⏹ Arrêt demandé par l'utilisateur.")
        tts.say("Arrêt du script")
        tts.runAndWait()
