
# READ-FOR-ME Multimeter

## Introduction

Ce code de test préliminaire et de validation du concept permet de lire l’état du multimètre Owon 16 et annoncer les mesures sur un raspberry PI 5 :

* `setup_env_rpi.sh` script pour installer et lancer la reconnaissance ble
* `requirements.txt` (peut-être incomplet ?)
* `ble_scan_test.py` script pour détecter le ble du multimètre
* `owon_ble_monitor_*.py`  plusieurs codes python de test pour annoncer les données envoyées par l’OWon 16 (différentes version)
* `owon_decoder.py` module Python avec la classe qui permet de décommuter les 6 octets envoyés par l’OWon 16 sur la liaison BLE
* `owon_monitor_parameters.json`
* `code_validation_voix_tts.py` code pour lister les synthèses vocales disponibles sur le Raspberry PI 5 
* `liste_voix_disponibles.txt` résultats

Ces fichiers constituent une « preuve de concept » pour la fonction multimètre. Ils peuvent vous aider à démarrer le projet. Je vous demande juste d’être compréhensif à mon égard, dans la mesure où je ne suis pas informaticien de formation… 😉
