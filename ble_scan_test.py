
"""

   scanne le BLE pour essayer de trouver le multimetre owon 16 
  activer le BLE sur le PC avant de lancer ce script 
  
"""
import asyncio
import pandas as pd
from bleak import BleakScanner

output_file_name = "liste_devices.csv" 

async def scan_ble_devices(timeout: float = 8.0) -> pd.DataFrame:
    """
    Scanne les périphériques BLE et retourne un DataFrame pandas contenant leurs caractéristiques.
    """
    print(f"\n🔍 Scan BLE en cours ({timeout} secondes)...\n")
    devices = await BleakScanner.discover(timeout=timeout)

    rows = []
    for device in devices:
        name = device.name or "<inconnu>"
        mac = device.address
        rssi = device.rssi
        uuids = device.metadata.get("uuids")
        mfg_data = device.metadata.get("manufacturer_data")

        rows.append({
            "Nom": name,
            "Adresse MAC": mac,
            "RSSI (dBm)": rssi,
            "UUIDs": ", ".join(uuids) if uuids else "",
            "Manufacturer Data": str(mfg_data) if mfg_data else ""
        })

    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    df = asyncio.run(scan_ble_devices())
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 150)
    print(df)
    print(f"\n✅ {len(df)} périphérique(s) BLE détecté(s).\n")

    # Sauvegarde dans un fichier CSV avec séparateur point-virgule
    df.to_csv(output_file_name, sep=";", index=False, encoding="utf-8")
    print(f"Données enregistrées dans le fichier {output_file_name}")


