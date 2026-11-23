====================================================================
CABIN ANNOUNCEMENTS FOR FENIX A320 V3
Cleardeck Studio - version 2.0.0
====================================================================

FRANCAIS
--------

QU'EST-CE QUE C'EST ?
Un generateur d'annonces cabine pour le Fenix A320, dans la langue de
votre choix (associee a l'anglais, ou en anglais seul). Les annonces
sont fabriquees avec des voix neuronales Microsoft (plusieurs profils
d'equipage selon la langue) et s'adaptent a chaque vol : compagnie
aerienne, numero de vol, villes de depart et d'arrivee, meteo,
turbulences prevues, heure reelle (service repas/collation adapte au
moment de la journee, ambiance nuit si besoin), et un bruit de fond
discret qui s'adapte a la phase de vol (calme a l'embarquement,
reacteurs au roulage/en vol). Une fois installe, l'outil se connecte
et se ferme tout seul avec MSFS : rien a cliquer avant chaque vol.

COMPAGNIES RECONNUES AUTOMATIQUEMENT
La compagnie aerienne est reconnue automatiquement en vol, d'apres la
livree Fenix chargee dans le simulateur : rien a choisir dans le
programme. Compagnies actuellement prises en charge, avec leurs
propres annonces de service a bord :
  Eurowings, Transavia, Air France, Lufthansa, British Airways,
  easyJet.
Avec une autre livree, les annonces generiques (sans mention de
service specifique a la compagnie) sont utilisees automatiquement.

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
Double-cliquez sur CabinAnnouncementsFenixA320V3.exe. Une fenetre
s'ouvre et vous demande :
  - votre Pilot ID SimBrief (des chiffres uniquement) ;
  - votre dossier Community de MSFS 2024, avec un bouton "Parcourir..."
    (il est en general pre-rempli automatiquement si detecte) ;
  - la langue des annonces cabine (menu deroulant), 4 choix :
      * francais + anglais
      * allemand + anglais
      * espagnol + anglais
      * anglais seul
    Les champs de la fenetre sont affiches en francais ET en anglais.
Cliquez sur "Installation". La progression s'affiche dans la fenetre ;
cela prend plusieurs minutes la premiere fois (chaque annonce est
fabriquee pour plusieurs profils de voix, pour chaque compagnie
prise en charge). A la fin, un message confirme que tout est pret,
puis LA FENETRE SE FERME TOUTE SEULE. Ces informations sont
enregistrees dans config_cabine.json, a cote du programme. Le nom du
chef de cabine cite dans les annonces est choisi au hasard a chaque
nouvelle installation complete du pack (un seul nom par vol, pour
rester coherent du debut a la fin).

ET ENSUITE ? PLUS RIEN A FAIRE
A chaque lancement de MSFS 2024, le programme se connecte tout seul en
arriere-plan (aucune fenetre ne s'ouvre) : des qu'un vol commence, la
compagnie est reconnue d'apres la livree chargee, puis les annonces et
la meteo sont regenerees automatiquement a partir de votre dernier
plan SimBrief. A la fermeture de MSFS, le programme se ferme
automatiquement avec lui. Vous n'avez plus jamais besoin de relancer
CabinAnnouncementsFenixA320V3.exe vous-meme pour voler : il suffit de
deposer votre plan de vol sur SimBrief, choisir votre livree, puis
lancer MSFS.
IMPORTANT : si MSFS 2024 etait deja ouvert pendant l'installation,
fermez-le puis relancez-le une fois pour activer la connexion
automatique (elle ne s'active qu'au demarrage de MSFS).
Cette connexion automatique fonctionne comme vos autres outils tiers
(GSX, AIG, TrackIR...) : une ligne est ajoutee dans la configuration
de lancement automatique de MSFS. Rien n'est modifie en dehors de
cette ligne.

POUR RECONFIGURER (changer de langue, de dossier Community, etc.)
Relancez CabinAnnouncementsFenixA320V3.exe en double-cliquant dessus :
la fenetre d'installation revient avec vos reglages actuels, modifiez
ce qu'il faut et cliquez a nouveau sur "Mettre a jour".

DESINSTALLER
Un onglet "Desinstaller / Uninstall" dans la meme fenetre permet de
tout retirer proprement : le pack audio genere, la connexion
automatique avec MSFS, le raccourci sur le Bureau, le fichier de
configuration, et le programme lui-meme. Rien d'autre n'est touche
(MSFS, Fenix, vos livrees et vos autres add-ons restent intacts).

COMMANDES AVANCEES (optionnel, ligne de commande)
  CabinAnnouncementsFenixA320V3.exe --vol
      Regenere manuellement les annonces du vol en cours.
  CabinAnnouncementsFenixA320V3.exe --tout
      Regenere tout manuellement (annonces generiques + vol).
  CabinAnnouncementsFenixA320V3.exe --test-voix
      Verifie que les profils de voix de la langue choisie repondent.
Ces commandes ne sont utiles qu'en depannage : en usage normal, la
connexion automatique avec MSFS (ci-dessus) suffit.

OU VA LE RESULTAT ?
Le pack est ecrit dans votre dossier Community, sous
fnx-cabin-announcements-cleardeck\AirlinePacks\<code compagnie>
(par exemple AFR pour Air France, EWG/EWL pour Eurowings). Le
Fenix A320 le lit automatiquement au prochain vol, selon la livree
chargee.

BESOIN D'AIDE ?
Reconfigurer depuis le debut (par exemple pour changer de langue) :
supprimez le fichier config_cabine.json situe a cote de
l'executable, puis relancez le programme.
En cas de souci avec la reconnaissance automatique de compagnie ou
l'heure reelle en vol, un journal de diagnostic (debug_simconnect.log,
a cote du programme) peut etre consulte ou envoye a Cleardeck Studio.

A PROPOS
Cleardeck Studio - outils gratuits pour simmers MSFS 2024.
D'autres outils (suivi de carriere virtuelle, copilote virtuel pour
le Fenix A320) sont a venir.


ENGLISH
-------

WHAT IS THIS?
A cabin announcement generator for the Fenix A320, in the language of
your choice (paired with English, or English only). Announcements are
built with Microsoft neural voices (several crew voice profiles
depending on the language) and are tailored to each flight: airline,
flight number, departure/arrival cities, weather, expected
turbulence, real time of day (meal/snack service adapted to the time
of day, night-flight ambiance when relevant), and a subtle background
ambiance that adapts to the flight phase (quiet during boarding,
engine hum while taxiing/in flight). Once installed, the tool
connects and closes itself together with MSFS: nothing to click
before each flight.

AUTOMATICALLY RECOGNISED AIRLINES
The airline is recognised automatically in flight, from the Fenix
livery loaded in the simulator: nothing to choose in the program.
Airlines currently supported, each with its own onboard-service
announcements:
  Eurowings, Transavia, Air France, Lufthansa, British Airways,
  easyJet.
With any other livery, generic announcements (with no airline-specific
service mention) are used automatically.

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
Double-click CabinAnnouncementsFenixA320V3.exe. A window opens and
asks for:
  - your SimBrief Pilot ID (digits only);
  - your MSFS 2024 Community folder, with a "Browse..." button
    (usually pre-filled automatically if detected);
  - the cabin announcement language (dropdown menu), 4 choices:
      * French + English
      * German + English
      * Spanish + English
      * English only
    Every field in the window is labeled in both French and English.
Click "Install". Progress is shown in the window; the first run takes
a few minutes (every announcement is built for several voice
profiles, for every supported airline). When done, a message confirms
everything is ready, then THE WINDOW CLOSES BY ITSELF. These settings
are saved to config_cabine.json next to the program. The cabin
manager's name mentioned in the announcements is picked at random on
every full reinstall of the pack (one single name per flight, kept
consistent from start to finish).

WHAT NOW? NOTHING ELSE TO DO
Every time MSFS 2024 starts, the program connects by itself in the
background (no window opens): as soon as a flight begins, the airline
is recognised from the loaded livery, then the announcements and
weather are regenerated automatically from your latest SimBrief plan.
When MSFS closes, the program closes automatically with it. You never
need to run CabinAnnouncementsFenixA320V3.exe yourself to fly again:
just file your flight plan on SimBrief, pick your livery, then start
MSFS.
IMPORTANT: if MSFS 2024 was already running during installation,
close it and start it again once to activate the automatic
connection (it only activates when MSFS starts).
This automatic connection works the same way as your other
third-party tools (GSX, AIG, TrackIR...): one line is added to MSFS's
automatic-launch configuration. Nothing else is changed.

TO RECONFIGURE (change language, Community folder, etc.)
Double-click CabinAnnouncementsFenixA320V3.exe again: the install
window reopens with your current settings, change what you need and
click "Update" again.

UNINSTALLING
An "Uninstall" tab in the same window cleanly removes everything: the
generated audio pack, the automatic connection with MSFS, the Desktop
shortcut, the configuration file, and the program itself. Nothing
else is touched (MSFS, Fenix, your liveries and your other add-ons
stay untouched).

ADVANCED COMMANDS (optional, command line)
  CabinAnnouncementsFenixA320V3.exe --vol
      Manually regenerates the current flight's announcements.
  CabinAnnouncementsFenixA320V3.exe --tout
      Manually regenerates everything (generic + flight-specific).
  CabinAnnouncementsFenixA320V3.exe --test-voix
      Checks that the chosen language's voice profiles respond.
These commands are only useful for troubleshooting: in normal use,
the automatic connection with MSFS (above) is all you need.

WHERE DOES THE OUTPUT GO?
The pack is written to your Community folder, under
fnx-cabin-announcements-cleardeck\AirlinePacks\<airline code>
(for example AFR for Air France, EWG/EWL for Eurowings). The Fenix
A320 reads this pack automatically on your next flight, according to
the loaded livery.

NEED HELP?
To start configuration over (for example to change the language),
delete config_cabine.json next to the program and run it again.
If automatic airline recognition or the real in-flight time ever
look wrong, a diagnostic log (debug_simconnect.log, next to the
program) can be checked or sent to Cleardeck Studio.

ABOUT
Cleardeck Studio - free tools for MSFS 2024 simmers.
More tools (virtual career tracker, virtual co-pilot for the Fenix
A320) are coming.
