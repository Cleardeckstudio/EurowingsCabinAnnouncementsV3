====================================================================
CABIN ANNOUNCEMENTS FOR FENIX A320 V3
Cleardeck Studio - version 2.0.0
====================================================================

FRANCAIS
--------

QU'EST-CE QUE C'EST ?
Un generateur d'annonces cabine pour le Fenix A320, dans la langue de
votre choix (associee a l'anglais, ou en anglais seul). La compagnie
est reconnue automatiquement d'apres la livree active au demarrage du
vol (immatriculation) : aucune selection manuelle n'est necessaire,
et l'outil fonctionne avec n'importe quelle livree Fenix A320
installee, pas seulement Eurowings. Les annonces sont fabriquees avec
des voix neuronales Microsoft (jusqu'a 20 profils d'equipage
differents selon la langue, une seule voix fixe par vol) et
s'adaptent a chaque vol : numero de vol, villes de depart et
d'arrivee, meteo en temps reel, retards eventuels et turbulences
prevues. Une fois installe, l'outil se connecte et se ferme tout seul
avec MSFS : rien a cliquer avant chaque vol.

NOUVEAU DANS CETTE VERSION (2.0.0)
  - Reconnaissance automatique de la compagnie : plus besoin de
    choisir une livree a l'installation, elle est detectee par
    immatriculation a chaque vol.
  - Synchronisation en direct avec GSX Pro : annonces au commandant au
    debut et a la fin de l'embarquement (avec le nombre de passagers
    prevu) et du debarquement, en plus des annonces passagers.
  - Installation automatique du pont MobiFlight (necessaire a la
    synchronisation GSX) si GSX Pro est detecte et que le pont n'est
    pas deja present.
  - Un onglet de desinstallation complete, integre a la fenetre de
    l'outil (ne touche jamais a MSFS, au Fenix ni a vos livrees).
  - Voix du chef de cabine et du commandant rendue coherente sur
    l'ensemble d'un vol (une seule voix, plus de changement en cours
    de vol).
  - Prononciation des noms de compagnie amelioree dans les 4 langues
    (ex: "Air France" correctement prononce, au lieu d'etre lu comme
    un seul bloc).

CE QU'IL VOUS FAUT AVANT DE COMMENCER
1. Un compte SimBrief gratuit (www.simbrief.com), avec votre
   "Pilot ID" (dans Account > Pilot ID).
2. MSFS 2024 avec le Fenix A320 installe (n'importe quelle livree).
3. Une connexion internet : le programme interroge SimBrief et les
   voix Microsoft a chaque generation. Sans internet, il ne fonctionne
   pas.
4. IMPORTANT : ce programme ne cree PAS de plan de vol. Deposez votre
   plan de vol sur SimBrief (dispatch.simbrief.com) AVANT chaque vol :
   c'est ce plan qui donne le numero de vol, les villes et la meteo
   annoncee en cabine. Sans plan de vol recent sur SimBrief, les
   annonces ne correspondront pas a votre vol.
5. Facultatif : GSX Pro, pour les annonces en direct au commandant au
   fil de l'embarquement/debarquement (le pont MobiFlight necessaire
   est installe automatiquement si besoin).

INSTALLATION (une seule fois)
Double-cliquez sur EurowingsCabinAnnouncementsV3.exe. Une fenetre
intitulee "Cabin Announcements for Fenix A320 V3" s'ouvre et vous
demande :
  - votre Pilot ID SimBrief (des chiffres uniquement) ;
  - votre dossier Community de MSFS 2024, avec un bouton "Parcourir..."
    (il est en general pre-rempli automatiquement si detecte) ;
  - la langue des annonces cabine (menu deroulant), 4 choix :
      * francais + anglais
      * allemand + anglais
      * espagnol + anglais
      * anglais seul
    Les champs de la fenetre sont affiches en francais ET en anglais.
C'est tout : il n'y a plus de choix de compagnie a faire, elle sera
reconnue automatiquement a chaque vol. Cliquez sur "Installation". La
progression s'affiche dans la fenetre ; cela prend plusieurs minutes
la premiere fois (chaque annonce est fabriquee pour plusieurs profils
de voix). A la fin, un message confirme que tout est pret, puis LA
FENETRE SE FERME TOUTE SEULE. Ces informations sont enregistrees dans
config_cabine.json, a cote du programme.

ET ENSUITE ? PLUS RIEN A FAIRE
A chaque lancement de MSFS 2024, le programme se connecte tout seul en
arriere-plan (aucune fenetre ne s'ouvre) : des qu'un vol commence, la
compagnie active est reconnue automatiquement, et les annonces et la
meteo sont regenerees a partir de votre dernier plan SimBrief. Si GSX
Pro est utilise, les annonces au commandant suivent en direct
l'embarquement et le debarquement. A la fermeture de MSFS, le
programme se ferme automatiquement avec lui. Vous n'avez plus jamais
besoin de relancer l'executable vous-meme pour voler : il suffit de
deposer votre plan de vol sur SimBrief puis de lancer MSFS.
IMPORTANT : si MSFS 2024 etait deja ouvert pendant l'installation,
fermez-le puis relancez-le une fois pour activer la connexion
automatique (elle ne s'active qu'au demarrage de MSFS).
Cette connexion automatique fonctionne comme vos autres outils tiers
(GSX, AIG, TrackIR...) : une ligne est ajoutee dans la configuration
de lancement automatique de MSFS. Rien n'est modifie en dehors de
cette ligne.

POUR RECONFIGURER (changer de langue, d'identifiant SimBrief, etc.)
Un raccourci "Cabin Announcements for Fenix A320 V3" est cree sur
votre Bureau au premier lancement : ouvrez-le, la fenetre revient avec
vos reglages actuels (le bouton s'appelle alors "Mettre a jour /
Update"), modifiez ce qu'il faut et cliquez dessus.
Si vous changez la langue, les annonces sont regenerees dans la
nouvelle langue et remplacent celles de l'ancienne langue (elles ne
sont pas conservees en parallele).

DESINSTALLATION
Ouvrez l'outil (double-clic sur l'executable ou sur le raccourci
Bureau), puis l'onglet "Desinstaller / Uninstall". Cela retire
proprement : la connexion automatique avec MSFS, le pack audio genere
dans Community, le raccourci Bureau, le fichier de configuration, et
le dossier du programme lui-meme. Rien d'autre n'est touche : ni MSFS,
ni le Fenix, ni vos livrees, ni vos autres add-ons.

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
fnx-cabin-announcements-cleardeck\AirlinePacks\<code compagnie>. Le
Fenix A320 le lit automatiquement au prochain vol.

BESOIN D'AIDE ?
Reconfigurer depuis le debut (par exemple pour changer de langue) :
utilisez le raccourci Bureau (voir "POUR RECONFIGURER" ci-dessus), ou
en dernier recours supprimez le fichier config_cabine.json situe a
cote de l'executable puis relancez le programme.

A PROPOS
Cleardeck Studio - outils gratuits pour simmers MSFS 2024.
D'autres outils (suivi de carriere virtuelle, copilote virtuel pour
le Fenix A320) sont a venir.


ENGLISH
-------

WHAT IS THIS?
A cabin announcement generator for the Fenix A320, in the language of
your choice (paired with English, or English only). The airline is
recognised automatically from the active livery at the start of each
flight (registration number): no manual selection is needed, and the
tool works with any Fenix A320 livery installed, not just Eurowings.
Announcements are built with Microsoft neural voices (up to 20
different crew voice profiles depending on the language, one fixed
voice per flight) and are tailored to each flight: flight number,
departure/arrival cities, real-time weather, delays and expected
turbulence. Once installed, the tool connects and closes itself
together with MSFS: nothing to click before each flight.

NEW IN THIS VERSION (2.0.0)
  - Automatic airline recognition: no need to pick a livery during
    install anymore, it is detected by registration on every flight.
  - Live GSX Pro sync: announcements to the captain at the start and
    end of boarding (with the expected passenger count) and
    deboarding, alongside the passenger announcements.
  - Automatic install of the MobiFlight bridge (required for GSX
    sync) if GSX Pro is detected and the bridge is not already there.
  - A full uninstall tab built into the tool's own window (never
    touches MSFS, the Fenix, or your liveries).
  - Consistent cabin-manager/captain voice throughout a flight (one
    voice, no more switching mid-flight).
  - Improved airline-name pronunciation across all 4 languages (e.g.
    "Air France" now pronounced correctly instead of as one block).

WHAT YOU NEED BEFORE YOU START
1. A free SimBrief account (www.simbrief.com), and your Pilot ID
   (Account > Pilot ID).
2. MSFS 2024 with the Fenix A320 installed (any livery).
3. An internet connection: the program queries SimBrief and
   Microsoft's voices every time it runs. It will not work offline.
4. IMPORTANT: this tool does NOT create a flight plan. File your
   flight plan on SimBrief (dispatch.simbrief.com) BEFORE each
   flight: that plan supplies the flight number, cities and weather
   you hear in the cabin. Without a recent SimBrief plan, the
   announcements will not match your flight.
5. Optional: GSX Pro, for live captain announcements during
   boarding/deboarding (the required MobiFlight bridge is installed
   automatically if needed).

INSTALLATION (one time only)
Double-click EurowingsCabinAnnouncementsV3.exe. A window titled
"Cabin Announcements for Fenix A320 V3" opens and asks for:
  - your SimBrief Pilot ID (digits only);
  - your MSFS 2024 Community folder, with a "Browse..." button
    (usually pre-filled automatically if detected);
  - the cabin announcement language (dropdown menu), 4 choices:
      * French + English
      * German + English
      * Spanish + English
      * English only
    Every field in the window is labeled in both French and English.
That's it: there is no airline/livery choice to make anymore, it will
be recognised automatically on every flight. Click "Install". Progress
is shown in the window; the first run takes a few minutes (every
announcement is built for several voice profiles). When done, a
message confirms everything is ready, then THE WINDOW CLOSES BY
ITSELF. These settings are saved to config_cabine.json next to the
program.

WHAT NOW? NOTHING ELSE TO DO
Every time MSFS 2024 starts, the program connects by itself in the
background (no window opens): as soon as a flight begins, the active
airline is recognised automatically, and the announcements and
weather are regenerated from your latest SimBrief plan. If GSX Pro is
in use, captain announcements follow boarding and deboarding live.
When MSFS closes, the program closes automatically with it. You never
need to run the executable yourself to fly again: just file your
flight plan on SimBrief, then start MSFS.
IMPORTANT: if MSFS 2024 was already running during installation,
close it and start it again once to activate the automatic
connection (it only activates when MSFS starts).
This automatic connection works the same way as your other
third-party tools (GSX, AIG, TrackIR...): one line is added to MSFS's
automatic-launch configuration. Nothing else is changed.

TO RECONFIGURE (change language, SimBrief ID, etc.)
A "Cabin Announcements for Fenix A320 V3" shortcut is created on your
Desktop on first launch: open it, the window reopens with your
current settings (the button is now labeled "Update"), change what
you need and click it.
If you change the language, announcements are regenerated in the new
language and replace the previous language's files (the two are not
kept side by side).

UNINSTALLING
Open the tool (double-click the executable or the Desktop shortcut),
then the "Desinstaller / Uninstall" tab. This cleanly removes: the
automatic connection with MSFS, the generated audio pack in Community,
the Desktop shortcut, the configuration file, and the program's own
folder. Nothing else is touched: not MSFS, not the Fenix, not your
liveries, not your other add-ons.

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
fnx-cabin-announcements-cleardeck\AirlinePacks\<airline code>. The
Fenix A320 reads this pack automatically on your next flight.

NEED TO RESET?
To start configuration over (for example to change the language), use
the Desktop shortcut (see "TO RECONFIGURE" above), or as a last
resort delete config_cabine.json next to the program and run it
again.

ABOUT
Cleardeck Studio - free tools for MSFS 2024 simmers.
More tools (virtual career tracker, virtual co-pilot for the Fenix
A320) are coming.
