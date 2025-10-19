
"""

 pour validation des propriétés de l'objet tts (pyttsx3)

"""
def print_tts_properties():
    """Affiche la configuration actuelle de la synthèse vocale TTS."""
    print("\n=== Configuration actuelle de la synthèse vocale ===")
    print(f"Débit (rate)    : {tts.getProperty('rate')}")
    print(f"Volume (volume) : {tts.getProperty('volume')}")
    print(f"Voix sélectionnée (voice id) : {tts.getProperty('voice')}")
    voices = tts.getProperty('voices')
    print(f"Nombre total de voix disponibles : {len(voices)}")
    for i, voice in enumerate(voices):
        print(f"Voix {i} : {voice.id} - {voice.name} - Langues : {voice.languages}")
    print("====================================================\n")

# test
print_tts_properties()
