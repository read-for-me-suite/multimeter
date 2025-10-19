#!/bin/bash

echo "🔧 [1/5] Mise à jour du système..."
sudo apt update && sudo apt install -y espeak libespeak1 python3-venv

echo "📁 [2/5] Création de l'environnement virtuel Python 3.11..."
python3.11 -m venv venv

echo "🚀 [3/5] Activation de l'environnement virtuel..."
source venv/bin/activate

echo "📦 [4/5] Installation des dépendances Python..."
pip install --upgrade pip
pip install bleak pyttsx3

echo "🎬 [5/5] Lancement du script de surveillance OWON 16..."
python owon_ble_monitor_rpi.py
