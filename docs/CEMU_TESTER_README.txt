CTGP-Cafe MK8 + Protarium Network - paquet de test Cemu (build P46, 2026-11-06)
===============================================================================

CE QU'IL FAUT
- Cemu (2.x) avec Mario Kart 8 EUROPE + mise a jour v81 (titre 0005000E-1010ED00) deja installee.
- Un compte Protarium Network (PNID) lie a ton Cemu (compte en ligne actif).
- Le fichier network_services.xml de Protarium (fourni: network_services.xml.protarium).

INSTALLATION
1. FERME Cemu.
2. Sauvegarde ton dossier  <Cemu>/mlc01/usr/title/0005000e/1010ed00  (au minimum code/Turbo.rpx et code/cos.xml).
3. Copie le dossier "mlc01" de ce ZIP dans le dossier de Cemu (celui qui contient deja mlc01) et accepte de FUSIONNER/REMPLACER.
   Ca remplace code/Turbo.rpx et code/cos.xml et ajoute les fichiers CTGP dans content/.
4. Reseau: copie network_services.xml.protarium dans <Cemu>/ sous le nom  network_services.xml  (garde l'ancien en .bak).
5. Lance Mario Kart 8 depuis Cemu.

JEU EN LIGNE (serveur Protarium)
- Mode CTGP: Online > Worldwide. Ce build demande son propre pool de matchmaking (game server 1010EB01):
  tu ne croises que des joueurs avec ce meme pack.
- Dis ton PID au testeur si on te le demande pour les logs (pas de liste blanche sur ce pool).

CE QUI MARCHE / NE MARCHE PAS ENCORE
- OK: connexion, matchmaking Worldwide, vote de circuit (teste sur 1 joueur).
- Pas encore: noms/vignettes des CT sur les cartes du vote (elles montrent les circuits natifs), envoi de ghosts CTGP
  (la liste "Plus de fantomes" fonctionne en local), test a plusieurs joueurs.
- Si le jeu plante au demarrage: ton Cemu n'a pas la v81 EUR, ou tu as oublie de fusionner tout le dossier mlc01.

DESINSTALLER
Remets les fichiers sauvegardes a l'etape 2 (le contenu CTGP ajoute dans content/ peut rester, il n'est pas utilise sans le Turbo.rpx CTGP).
