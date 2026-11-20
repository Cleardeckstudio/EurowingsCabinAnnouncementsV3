====================================================================
EUROWINGS CABIN ANNOUNCEMENTS V3 - FENIX A320
Cleardeck Studio - version 1.2.0
====================================================================

FRANCAIS
--------

QU'EST-CE QUE C'EST ?
Un generateur d'annonces cabine pour le Fenix A320, dans le style
Eurowings, dans la langue de votre choix (associee a l'anglais, ou en
anglais seul). Les annonces sont fabriquees avec des voix neuronales
Microsoft (jusqu'a 20 profils d'equipage differents selon la langue)
et s'adaptent a chaque vol : numero de vol, villes de depart et
d'arrivee, meteo, et turbulences prevues. Une fois installe, l'outil
se connecte et se ferme tout seul avec MSFS : rien a cliquer avant
chaque vol.

CE QU'IL VOUS FAUT AVANT DE COMMENCER
1. Un compte SimBrief gratuit (www.simbrief.com), avec votre
   "Pilot ID" (dans Account > Pilot ID).
2. MSFS 2024 avec le Fenix A320 installe.
3. Une connexion internet : le programme interroge SimBrief et les
   voix Microsoft a chaque generation. Sans internet, il ne fonctionne
   pas.
4. IMPORTANT : ce programme ne cree PAS de plan de vol. Deposez votre
   plan de vol sur SimBrief (dispatch.simbrief.com) AVANT chaque vol :
   c'est ce plan qui donne le numero de vol, les villes et la meteo
   annoncee en cabine. Sans plan de vol recent sur SimBrief, les
   annonces ne correspondront pas a votre vol.

INSTALLATION (une seule fois)
Double-cliquez sur EurowingsCabinAnnouncementsV3.exe. Une fenetre
s'ouvre et vous demande :
  - votre Pilot ID SimBrief (des chiffres uniquement) ;
  - votre dossier Community de MSFS 2024, avec un bouton "Parcourir..."
    (il est en general pre-rempli automatiquement si detecte) ;
  - la langue des annonces cabine (menu deroulant), 4 choix :
      * francais + anglais
      * allemand + anglais
      * espagnol + anglais
      * anglais seul
    Les champs de la fenetre sont affiches en francais ET en anglais ;
  - le nom du commandant / chef de cabine a citer dans les annonces
    (facultatif, laissez vide si vous ne voulez pas en utiliser).
Cliquez sur "Installation". La progression s'affiche dans la fenetre ;
cela prend plusieurs minutes la premiere fois (chaque annonce est
fabriquee pour plusieurs profils de voix). A la fin, un message
confirme que tout est pret, puis LA FENETRE SE FERME TOUTE SEULE.
Ces informations sont enregistrees dans config_cabine.json, a cote du
programme.

ET ENSUITE ? PLUS RIEN A FAIRE
A chaque lancement de MSFS 2024, le programme se connecte tout seul en
arriere-plan (aucune fenetre ne s'ouvre) : des qu'un vol commence, les
annonces et la meteo sont regenerees automatiquement a partir de votre
dernier plan SimBrief. A la fermeture de MSFS, le programme se ferme
automatiquement avec lui. Vous n'avez plus jamais besoin de relancer
EurowingsCabinAnnouncementsV3.exe vous-meme pour voler : il suffit de
deposer votre plan de vol sur SimBrief puis de lancer MSFS.
IMPORTANT : si MSFS 2024 etait deja ouvert pendant l'installation,
fermez-le puis relancez-le une fois pour activer la connexion
automatique (elle ne s'active qu'au demarrage de MSFS).
Cette connexion automatique fonctionne comme vos autres outils tiers
(GSX, AIG, TrackIR...) : une ligne est ajoutee dans la configuration
de lancement automatique de MSFS. Rien n'est modifie en dehors de
cette ligne.

POUR RECONFIGURER (changer de langue, de nom, etc.)
Relancez EurowingsCabinAnnouncementsV3.exe en double-cliquant dessus :
la fenetre d'installation revient avec vos reglages actuels, modifiez
ce qu'il faut et cliquez a nouveau sur "Installation".

COMMANDES AVANCEES (optionnel, ligne de commande)
  EurowingsCabinAnnouncementsV3.exe --vol
      Regenere manuellement les annonces du vol en cours.
  EurowingsCabinAnnouncementsV3.exe --tout
      Regenere tout manuellement (annonces generiques + vol).
  EurowingsCabinAnnouncementsV3.exe --test-voix
      Verifie que les profils de voix de la langue choisie repondent.
Ces commandes ne sont utiles qu'en depannage : en usage normal, la
connexion automatique avec MSFS (ci-dessus) suffit.

OU VA LE RESULTAT ?
Le pack est ecrit dans votre dossier Community, sous
fnx-airline-packs-eurowings\AirlinePacks. Le Fenix A320 le lit
automatiquement au prochain vol.

BESOIN D'AIDE ?
Reconfigurer depuis le debut (par exemple pour changer de langue) :
supprimez le fichier config_cabine.json situe a cote de
l'executable, puis relancez le programme.

A PROPOS
Cleardeck Studio - outils gratuits pour simmers MSFS 2024.
D'autres outils (suivi de carriere virtuelle, copilote virtuel pour
le Fenix A320) sont a venir.


ENGLISH
-------

WHAT IS THIS?
A cabin announcement generator for the Fenix A320, Eurowings style,
in the language of your choice (paired with English, or English
only). Announcements are built with Microsoft neural voices (up to
20 different crew voice profiles depending on the language) and are
tailored to each flight: flight number, departure/arrival cities,
weather, and expected turbulence. Once installed, the tool connects
and closes itself together with MSFS: nothing to click before each
flight.

WHAT YOU NEED BEFORE YOU START
1. A free SimBrief account (www.simbrief.com), and your Pilot ID
   (Account > Pilot ID).
2. MSFS 2024 with the Fenix A320 installed.
3. An internet connection: the program queries SimBrief and
   Microsoft's voices every time it runs. It will not work offline.
4. IMPORTANT: this tool does NOT create a flight plan. File your
   flight plan on SimBrief (dispatch.simbrief.com) BEFORE each
   flight: that plan supplies the flight number, cities and weather
   you hear in the cabin. Without a recent SimBrief plan, the
   announcements will not match your flight.

INSTALLATION (one time only)
Double-click EurowingsCabinAnnouncementsV3.exe. A window opens and
asks for:
  - your SimBrief Pilot ID (digits only);
  - your MSFS 2024 Community folder, with a "Browse..." button
    (usually pre-filled automatically if detected);
  - the cabin announcement language (dropdown menu), 4 choices:
      * French + English
      * German + English
      * Spanish + English
      * English only
    Every field in the window is labeled in both French and English;
  - the captain's / cabin manager's name to mention in the
    announcements (optional, leave blank to skip).
Click "Install". Progress is shown in the window; the first run takes
a few minutes (every announcement is built for several voice
profiles). When done, a message confirms everything is ready, then
THE WINDOW CLOSES BY ITSELF. These settings are saved to
config_cabine.json next to the program.

WHAT NOW? NOTHING ELSE TO DO
Every time MSFS 2024 starts, the program connects by itself in the
background (no window opens): as soon as a flight begins, the
announcements and weather are regenerated automatically from your
latest SimBrief plan. When MSFS closes, the program closes
automatically with it. You never need to run
EurowingsCabinAnnouncementsV3.exe yourself to fly again: just file
your flight plan on SimBrief, then start MSFS.
IMPORTANT: if MSFS 2024 was already running during installation,
close it and start it again once to activate the automatic
connection (it only activates when MSFS starts).
This automatic connection works the same way as your other
third-party tools (GSX, AIG, TrackIR...): one line is added to MSFS's
automatic-launch configuration. Nothing else is changed.

TO RECONFIGURE (change language, name, etc.)
Double-click EurowingsCabinAnnouncementsV3.exe again: the install
window reopens with your current settings, change what you need and
click "Install" again.

ADVANCED COMMANDS (optional, command line)
  EurowingsCabinAnnouncementsV3.exe --vol
      Manually regenerates the current flight's announcements.
  EurowingsCabinAnnouncementsV3.exe --tout
      Manually regenerates everything (generic + flight-specific).
  EurowingsCabinAnnouncementsV3.exe --test-voix
      Checks that the chosen language's voice profiles respond.
These commands are only useful for troubleshooting: in normal use,
the automatic connection with MSFS (above) is all you need.

WHERE DOES THE OUTPUT GO?
The pack is written to your Community folder, under
fnx-airline-packs-eurowings\AirlinePacks. The Fenix A320 reads this
pack automatically on your next flight.

NEED TO RESET?
To start configuration over (for example to change the language),
delete config_cabine.json next to the program and run it again.

ABOUT
Cleardeck Studio - free tools for MSFS 2024 simmers.
More tools (virtual career tracker, virtual co-pilot for the Fenix
A320) are coming.
