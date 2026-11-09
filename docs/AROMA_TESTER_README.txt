CTGP-Cafe MK8 (Wii U, Aroma) + serveur Protarium - paquet de test (2026-11-06)
==============================================================================

STATUT: NON TESTE SUR UNE VRAIE WII U. Base = pack R7 (valide en Cemu), avec le serveur de jeu Protarium.

CE QU'IL FAUT
- Wii U sous Aroma (modules ContentRedirection + Notifications), Mario Kart 8 EUROPE, mise a jour v81 (titre 000500001010ED00).
- Carte SD FAT32 avec ~5 Go libres.
- Un compte Protarium Network (PNID) sur la console, et la console connectee au reseau Protarium (Inkay/patch de reseau).

INSTALLATION
1. Sauvegarde ta carte SD.
2. Copie le CONTENU du dossier "sd" a la RACINE de la SD (fusion / remplacer).
3. Une seule copie de mk8-ct.wps doit etre active dans sd:/wiiu/environments/aroma/plugins/.
4. Demarre Aroma, lance Mario Kart 8. Online > Worldwide.

SERVEUR
- Ce pack demande l'identifiant de serveur de jeu 1010EB01 (pool de matchmaking CTGP de Protarium): tu ne croises que des joueurs avec ce pack.
- Pas de liste blanche sur ce pool.

LIMITES CONNUES
- Les cartes du vote Worldwide montrent encore les circuits natifs (noms/vignettes), pas les CT.
- Envoi/telechargement de ghosts CTGP en ligne: pas encore.
- Sois prudent: en cas de boucle de demarrage, retire mk8-ct.wps de la SD.

DESINSTALLER
Supprime sd:/wiiu/environments/aroma/plugins/mk8-ct.wps (et si tu veux sd:/cafeloader et sd:/wiiu/mk8-ct).
