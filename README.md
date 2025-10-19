Ce code de test préliminaire et de validation du concept permet de lire l’état du multimètre Owon 16 et annoncer les mesures sur un raspberry PI 5 :

    Du code pour lister les synthèses vocales disponibles sur le Raspberry PI 5
    L’environnement virtuel utilisé
    Le fichier requirements.txt (peut-être incomplet ?)
    Un module Python avec la classe qui permet de décommuter les 6 octets envoyés par l’OWon 16 sur la liaison BLE
    Plusieurs codes python de test pour annoncer les données envoyées par l’OWon 16 (différentes version) 

·       Un fichier de configuration json pour configurer les paramètres de la synthèse vocale.

 

Ces fichiers constituent une « preuve de concept » pour la fonction multimètre. Ils peuvent vous aider à démarrer le projet. Je vous demande juste d’être compréhensif à mon égard, dans la mesure où je ne suis pas informaticien de formation… 😉

 

Je vous demande de suivre les bonnes pratiques suivantes sur l’ensemble du projet :

    De bien veiller à documenter votre code python avec des Docstrings clairs et très détaillés au format NUMPY. Nous devons garder en têtte que le projet sera plublié en open source… la documentation du code doit être riche et comporter un grand nombre de commentaires. 

 

    Vous verrez dans mon code, des constantes __version__ et __date__ pour suivre les évolutions. 

 

    Enfin, j’ai une approche modulaire. Donc lorsque je développe une classe, en fin de code, j’ai toujours un bloc « if __name__ == « __main__ » : » afin de pouvoir tester ce module en mode ‘autonome ». 

Une fois la fonction validée on pourra l’intégrer au projet machine à lire. 
