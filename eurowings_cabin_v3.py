# -*- coding: utf-8 -*-
"""
pack_cabine.py : génère le pack d'annonces cabine Eurowings (français puis anglais) pour le Fenix A320.
- lit le dernier plan SimBrief (numéro de vol, villes, durée, météo départ et arrivée)
- fabrique les annonces avec les voix neuronales Microsoft (edge-tts), 20 profils de voix
- écrit le pack dans Community/fnx-airline-packs-eurowings/AirlinePacks/EWG (et EWL = code de la livrée 9H-EWF)

Usage :
  python pack_cabine.py --auto        nouveau plan SimBrief détecté ? alors régénère les annonces du vol (utilisé par Carrière)
  python pack_cabine.py --tout        régénère tout (annonces génériques + annonces du vol)
  python pack_cabine.py --vol         régénère uniquement les annonces du vol
  python pack_cabine.py --test-voix   teste que les 20 profils de voix répondent
"""
import asyncio, json, os, re, shutil, subprocess, sys, time, urllib.request, wave, math, struct, random, threading

import sys as _sys

def _here():
    if getattr(_sys, "frozen", False):
        return os.path.dirname(_sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

HERE = _here()
WORK = os.path.join(HERE, "pack_cabine")


def _recurso(nom):
    """Chemin vers un fichier embarque par PyInstaller (icone, etc.), ou a
    cote du script en mode non fige."""
    base = getattr(_sys, "_MEIPASS", HERE)
    return os.path.join(base, nom)
CONFIG_PATH = os.path.join(HERE, "config_cabine.json")
NB_PARALLELE = 5
VERSION = "2.0.0"
# Nom de produit affiche (fenetre, raccourci bureau, EXE.xml, desinstalleur).
# L'app n'est plus specifique a une seule compagnie (detection automatique
# de la compagnie active), d'ou le renommage ; NOMS_PRODUIT_ANCIENS liste les
# noms precedents a nettoyer automatiquement (EXE.xml, raccourci) pour que la
# migration d'une install existante ne laisse pas de doublon.
NOM_PRODUIT = "Cabin Announcements for Fenix A320 V3"
NOMS_PRODUIT_ANCIENS = ["Eurowings Cabin Announcements V3", "Fenix Cabin Announcements V3"]
NOM_RACCOURCI = "Cabin Announcements for Fenix A320 V3.lnk"
NOMS_RACCOURCI_ANCIENS = ["EurowingsCabinV3.lnk"]
COMPAGNIES_CONNUES = ('Aegean', 'Aer Lingus', 'Aeroflot', 'Afriqiyah Airways', 'Aigle Azur', 'Air Albania', 'Air Berlin', 'Air Cairo', 'Air Calin', 'Air Canada', 'Air China', 'Air Corsica', "Air Cote d'Ivoire", 'Air France', 'Air India', 'Air India Express', 'Air Jamaica', 'Air Juneyao', 'Air New Zealand', 'Air Nippon', 'Air Serbia', 'AirAsia', 'AirTran Airways', 'Alaska Airlines', 'Alitalia', 'All Leisure Airways', 'Allegiant Air', 'America West Airlines', 'American Airlines', 'ANA', 'Animawings', 'Ansett Australia', 'Astra Airlines', 'Austrian', 'Avianca', 'Azal', 'Azores Airlines', 'BA Euroflyer', 'Balkan Holidays', 'BCM Airlines', 'Berniq Airways', 'Bmi British Midland', 'Braniff Airways', 'British Airways', 'British Midland', 'Brussels Airlines', 'Bulgaria Airlines', 'Bulgaria Air', 'Caledonian Airways', 'Canada Jetlines', 'Canair', 'Cathay Dragon', 'Cebu Pacific Air', 'China Eastern', 'China Express', 'China Southern', 'Citilink', 'Condor', 'Constellation International', 'Corendon Airlines', 'Croatia Airlines', 'Cubana', 'Cyprus Airways', 'Delta Air Lines', 'Discover Airlines', 'Dragonair', 'Dutchbird', 'easyJet', 'easyJet Europe', 'easyJet Switzerland', 'Edelweiss', 'Egypt Air', 'Electra Airways', 'Etihad Airways', 'Eurofly', 'Eurowings', 'Eurowings Europe', 'EVA Air', 'Finnair', 'Flitestar Airways', 'Fly Air41 Airways', 'Fly Lili', 'Flyadeal', 'FlyArystan', 'Flynas', 'Flyniki', 'FlyOne', 'Frontier Airlines', 'Germanwings', 'Getjet', 'GlobalX', 'Hisky Europe', 'HK Express', 'Hong Kong Airlines', 'Iberia', 'Iberia Express', 'Iberworld Airlines', 'Indigo', 'Indonesia AirAsia', 'Iran Air', 'Iran Airtours', 'Iraqi Airways', 'ITA Airways', 'Jazeera Airways', 'JetBlue', 'Jetstar', 'Jetstar Asia', 'Jetstar Japan', 'JMC Air', 'LATAM Argentina', 'LATAM Brasil', 'LATAM Chile', 'LEAV', 'Level Europe', 'LTE International Airlines', 'LTU', 'LTU Austria', 'Lucky Air', 'Lufthansa', 'Martinair', 'Middle East Airlines', 'Midways Airlines', 'Monarch Airlines', 'Nile Air', 'Northwest Airlines', 'Nouvelair', 'Orange2Fly', 'Pegasus', 'Philippines AirAsia', 'PIA', 'QantasLink', 'Qatar Airways', 'Royal Jordanian', 'S7 Airlines', 'SAS', 'Saudi Arabian Airlines', 'Sichuan Airlines', 'SilkAir', 'Sobelair', 'Solomon', 'South African Airways', 'Spirit Airlines', 'SriLankan', 'Star East', 'StarFlyer', 'Sundair', 'Swiss', 'Syrian Air', 'TAP Air Portugal', 'Ted', 'Thai AirAsia', 'Thai Airways', 'Tigerair', 'Titan Airways', 'Trans-Meridian', 'TransAer International Airlines', 'Transavia', 'Translift Airways', 'TUI fly Belgium', 'TUI fly Netherlands', 'Turkish Airlines', 'United Airlines', 'Ural Airlines', 'US Airways', 'Uzbekistan Airways', 'Virgin America', 'Virgin Atlantic Airways', 'Virgin Sun', 'Viva Aerobus', 'Volotea', 'Vueling', 'White Airways', 'Wizz Air', 'Yamal Airlines')


def _candidats_community():
    appdata = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    return [
        os.path.join(local, "Packages", "Microsoft.Limitless_8wekyb3d8bbwe", "LocalCache", "Packages", "Community"),
        os.path.join(local, "Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "Packages", "Community"),
        os.path.join(appdata, "Microsoft Flight Simulator 2024", "Packages", "Community"),
        os.path.join(appdata, "Microsoft Flight Simulator", "Packages", "Community"),
    ]


def scanner_livrees_fenix(dossier_community):
    """Parcourt le dossier Community a la recherche de fichiers livery.cfg
    (format utilise par les livrees A320 Fenix, et plus generalement par
    toute livree au meme format) pour proposer directement au simmer la
    liste des livrees installees, au lieu de lui faire saisir la compagnie
    et le(s) code(s) ICAO a la main. Chaque entree retournee contient le
    nom lisible de la livree, la compagnie (atc_airline), le code ICAO
    reellement utilise par le moteur ATC/sons (icao_airline) et
    l'immatriculation (atc_id)."""
    resultats = []
    if not dossier_community or not os.path.isdir(dossier_community):
        return resultats
    for racine, dossiers, fichiers in os.walk(dossier_community):
        # on evite de descendre dans les gros dossiers de textures/modeles/sons
        # pour que le scan reste rapide (livery.cfg est toujours a la racine
        # du dossier de la livree)
        dossiers[:] = [d for d in dossiers if d.lower() not in
                       ("texture", "model", "sound", "html_ui", "panel", "effects")]
        if "livery.cfg" not in fichiers:
            continue
        chemin = os.path.join(racine, "livery.cfg")
        try:
            with open(chemin, encoding="utf-8-sig", errors="ignore") as f:
                contenu = f.read()
        except Exception:
            continue

        def _lire(cle, _c=contenu):
            m = re.search(r'^\s*%s\s*=\s*"?([^"\r\n]*)"?\s*$' % re.escape(cle), _c, re.MULTILINE | re.IGNORECASE)
            return m.group(1).strip() if m else ""

        icao = _lire("icao_airline")
        if not icao:
            continue  # pas un fichier de livree exploitable pour nos besoins
        resultats.append({
            "nom": _lire("name") or os.path.basename(racine),
            "compagnie": _lire("atc_airline") or icao,
            "icao": icao.upper(),
            "immat": _lire("atc_id"),
            "chemin": chemin,
        })

    vus, uniques = set(), []
    for r in resultats:
        cle = (r["compagnie"], r["icao"], r["immat"])
        if cle in vus:
            continue
        vus.add(cle)
        uniques.append(r)
    uniques.sort(key=lambda r: (r["compagnie"], r["immat"]))
    return uniques


def _charge_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _sauve_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


LANGUES = {
    "1": ("fr", "Francais + Anglais", "French + English"),
    "2": ("de", "Allemand + Anglais", "German + English"),
    "3": ("es", "Espagnol + Anglais", "Spanish + English"),
    "4": ("en", "Anglais seul", "English only"),
}


def premiere_configuration():
    """Au premier lancement : demande l'identifiant SimBrief, retrouve (ou demande) le
    dossier Community, et le choix de langue des annonces. Bilingue FR/EN car le
    pack est telecharge par des utilisateurs de nombreuses nationalites."""
    cfg = _charge_config()
    changer = False
    if not cfg.get("simbrief_id"):
        print("=" * 70)
        print("%s - premiere configuration" % NOM_PRODUIT)
        print("%s - first-time setup" % NOM_PRODUIT)
        print("=" * 70)
        print("Il vous faut un identifiant SimBrief (gratuit sur www.simbrief.com).")
        print("You need a SimBrief Pilot ID (free, on www.simbrief.com).")
        print("Vous le trouvez sur simbrief.com, menu Account > Pilot ID.")
        print("You can find it on simbrief.com, menu Account > Pilot ID.")
        while not cfg.get("simbrief_id"):
            v = input("Votre Pilot ID SimBrief / Your SimBrief Pilot ID (chiffres / digits only), puis Entree / then Enter : ").strip()
            if v.isdigit():
                cfg["simbrief_id"] = v; changer = True
            else:
                print("  -> ID invalide, recommencez. / Invalid ID, try again.")
    if not cfg.get("community") or not os.path.isdir(cfg.get("community", "")):
        trouve = next((c for c in _candidats_community() if os.path.isdir(c)), None)
        if trouve:
            print("Dossier Community detecte / Community folder detected : " + trouve)
            r = input("Utiliser ce dossier ? / Use this folder? (O/n - Y/n), puis Entree / then Enter : ").strip().lower()
            if r in ("", "o", "oui", "y", "yes"):
                cfg["community"] = trouve; changer = True
        while not cfg.get("community") or not os.path.isdir(cfg.get("community", "")):
            v = input("Chemin complet du dossier Community MSFS 2024 / Full path to your MSFS 2024 Community folder, puis Entree / then Enter : ").strip().strip('"')
            if os.path.isdir(v):
                cfg["community"] = v; changer = True
            else:
                print("  -> Dossier introuvable, recommencez. / Folder not found, try again.")
    if not cfg.get("langue") or cfg.get("langue") not in {v[0] for v in LANGUES.values()}:
        print("-" * 70)
        print("Choisissez la langue des annonces cabine / Choose the cabin announcement language :")
        for k, (code, fr, en) in LANGUES.items():
            print("  %s. %s / %s" % (k, fr, en))
        while not cfg.get("langue"):
            v = input("Votre choix (1-4) / Your choice (1-4), puis Entree / then Enter : ").strip()
            if v in LANGUES:
                cfg["langue"] = LANGUES[v][0]; changer = True
            else:
                print("  -> Choix invalide, recommencez. / Invalid choice, try again.")
    if "nom_equipage" not in cfg:
        print("-" * 70)
        print("Nom du commandant / chef de cabine a mentionner dans les annonces")
        print("(facultatif, laissez vide pour ne pas en utiliser) / Captain or cabin")
        print("manager's name to mention in the announcements (optional, leave")
        print("blank to skip), puis Entree / then Enter :")
        v = input("> ").strip()
        cfg["nom_equipage"] = v; changer = True
    if changer:
        _sauve_config(cfg)
        print("Configuration enregistree dans / Configuration saved to " + CONFIG_PATH)
        print("(Pour la refaire / to redo it : supprimez ce fichier et relancez / delete this file and run again.)\n")
    return cfg


if len(sys.argv) > 1 and "--auto-msfs" not in sys.argv[1:]:
    _CFG = premiere_configuration()
else:
    # mode GUI (double-clic), ou --auto-msfs (lance par MSFS, sans console ni
    # entree standard) : jamais de prompts interactifs ici.
    _CFG = _charge_config()
    if "--auto-msfs" in sys.argv[1:]:
        _manque = []
        if not _CFG.get("simbrief_id"):
            _manque.append("identifiant SimBrief")
        if not _CFG.get("community") or not os.path.isdir(_CFG.get("community", "")):
            _manque.append("dossier Community")
        if _manque:
            try:
                with open(os.path.join(HERE, "erreur_configuration.txt"), "w", encoding="utf-8") as _f:
                    _f.write(
                        "%s : configuration incomplete (%s).\n"
                        "Lancez le programme une premiere fois sans MSFS (double-clic sur\n"
                        "l'executable) pour faire la configuration via la fenetre, puis\n"
                        "relancez MSFS 2024.\n" % (NOM_PRODUIT, ", ".join(_manque))
                    )
            except Exception:
                pass
            sys.exit(0)
SIMBRIEF_ID = _CFG.get("simbrief_id", "")
COMMUNITY = _CFG.get("community", "")
NOM_EQUIPAGE = ""  # choisi automatiquement plus bas, une fois LANG connu
COMPAGNIE = (_CFG.get("compagnie") or "Eurowings").strip() or "Eurowings"
CODES = [c.strip().upper() for c in (_CFG.get("codes_compagnie") or "EWG,EWL").split(",") if c.strip()] or ["EWG", "EWL"]
PKG = os.path.join(COMMUNITY, "fnx-cabin-announcements-cleardeck") if COMMUNITY else ""
if COMMUNITY:
    _ancien_pkg = os.path.join(COMMUNITY, "fnx-airline-packs-eurowings")
    if os.path.isdir(_ancien_pkg) and _ancien_pkg != PKG:
        try:
            shutil.rmtree(_ancien_pkg)
        except Exception:
            pass
print("%s - version" % NOM_PRODUIT, VERSION)

# ------------------------------------------------------------------ voix
# (voix française, voix anglaise, débit, hauteur)
PROFILS_FR = [
    ("fr-FR-DeniseNeural", "en-GB-SoniaNeural", "+8%", "+0Hz"),
    ("fr-FR-DeniseNeural", "en-US-JennyNeural", "+6%", "+0Hz"),
    ("fr-FR-DeniseNeural", "en-GB-LibbyNeural", "+10%", "+2Hz"),
    ("fr-FR-DeniseNeural", "en-US-AriaNeural", "+6%", "-2Hz"),
    ("fr-FR-HenriNeural", "en-GB-RyanNeural", "+6%", "+0Hz"),
]
PROFILS_DE = [
    ("de-DE-TanjaNeural", "en-GB-SoniaNeural", "+6%", "+0Hz"),
    ("de-DE-ChristophNeural", "en-GB-RyanNeural", "+6%", "+0Hz"),
    ("de-DE-TanjaNeural", "en-US-JennyNeural", "+8%", "+2Hz"),
    ("de-DE-ChristophNeural", "en-US-GuyNeural", "+4%", "-2Hz"),
    ("de-DE-TanjaNeural", "en-GB-LibbyNeural", "+10%", "+0Hz"),
    ("de-DE-ChristophNeural", "en-GB-ThomasNeural", "+8%", "+0Hz"),
    ("de-DE-TanjaNeural", "en-US-AriaNeural", "+6%", "-2Hz"),
    ("de-DE-ChristophNeural", "en-GB-SoniaNeural", "+10%", "+2Hz"),
    ("de-DE-TanjaNeural", "en-US-AriaNeural", "+4%", "+0Hz"),
    ("de-DE-ChristophNeural", "en-US-AndrewNeural", "+6%", "+0Hz"),
    ("de-DE-TanjaNeural", "en-GB-MaisieNeural", "+8%", "+0Hz"),
    ("de-DE-ChristophNeural", "en-US-EricNeural", "+6%", "-2Hz"),
]
PROFILS_ES = [
    ("es-ES-ElviraNeural", "en-GB-SoniaNeural", "+6%", "+0Hz"),
    ("es-ES-AlvaroNeural", "en-GB-RyanNeural", "+6%", "+0Hz"),
    ("es-ES-XimenaNeural", "en-US-JennyNeural", "+8%", "+0Hz"),
    ("es-ES-AlvaroNeural", "en-US-GuyNeural", "+4%", "-2Hz"),
    ("es-ES-ElviraNeural", "en-GB-LibbyNeural", "+10%", "+0Hz"),
    ("es-ES-AlvaroNeural", "en-GB-ThomasNeural", "+8%", "+0Hz"),
    ("es-ES-XimenaNeural", "en-US-AriaNeural", "+6%", "-2Hz"),
    ("es-ES-AlvaroNeural", "en-GB-SoniaNeural", "+10%", "+2Hz"),
    ("es-ES-ElviraNeural", "en-US-AriaNeural", "+4%", "+0Hz"),
    ("es-ES-XimenaNeural", "en-US-AndrewNeural", "+6%", "+0Hz"),
    ("es-ES-ElviraNeural", "en-GB-MaisieNeural", "+8%", "+0Hz"),
    ("es-ES-AlvaroNeural", "en-US-EricNeural", "+6%", "-2Hz"),
]
PROFILS_EN = [
    ("en-GB-SoniaNeural", None, "+6%", "+0Hz"),
    ("en-GB-RyanNeural", None, "+6%", "+0Hz"),
    ("en-US-JennyNeural", None, "+8%", "+0Hz"),
    ("en-US-GuyNeural", None, "+6%", "+0Hz"),
    ("en-GB-LibbyNeural", None, "+8%", "+0Hz"),
    ("en-GB-ThomasNeural", None, "+6%", "+0Hz"),
    ("en-US-AriaNeural", None, "+8%", "-2Hz"),
    ("en-US-AndrewNeural", None, "+6%", "+0Hz"),
    ("en-GB-MaisieNeural", None, "+8%", "+0Hz"),
    ("en-US-AriaNeural", None, "+6%", "+0Hz"),
]
PROFILS_PAR_LANGUE = {"fr": PROFILS_FR, "de": PROFILS_DE, "es": PROFILS_ES, "en": PROFILS_EN}

# Prenoms (feminins) du chef de cabine, choisis au hasard selon la langue des
# annonces - plus besoin de les saisir a la main (ce sont toujours des femmes).
PRENOMS_CHEF_CABINE = {
    "fr": ["Camille", "Chloe", "Lea", "Manon", "Julie", "Sophie", "Charlotte", "Emma",
           "Lucie", "Marine", "Pauline", "Laura", "Amandine", "Elodie", "Claire"],
    "de": ["Anna", "Lena", "Sophie", "Lisa", "Laura", "Julia", "Sarah", "Marie",
           "Hannah", "Johanna", "Nina", "Katharina", "Melanie", "Christina", "Sabine"],
    "es": ["Lucia", "Sofia", "Martina", "Paula", "Carmen", "Laura", "Marta", "Elena",
           "Cristina", "Beatriz", "Patricia", "Isabel", "Rocio", "Alba", "Nuria"],
    "en": ["Emily", "Sarah", "Jessica", "Charlotte", "Olivia", "Hannah", "Amelia",
           "Grace", "Chloe", "Lauren", "Megan", "Emma", "Rebecca", "Laura", "Alice"],
}


def prenom_chef_cabine_aleatoire(langue):
    return random.choice(PRENOMS_CHEF_CABINE.get(langue, PRENOMS_CHEF_CABINE["en"]))


LANG = _CFG.get("langue", "fr")
SECONDE_LANGUE = None if LANG == "en" else "en"
PROFILS = PROFILS_PAR_LANGUE[LANG]
NOM_EQUIPAGE = prenom_chef_cabine_aleatoire(LANG)

# ------------------------------------------------------------------ villes (nom parlé)
VILLES = {
    "EDDV": ("Hanovre", "Hanover", "Hannover", "Hannover"), "EDDK": ("Cologne", "Cologne", "Köln", "Colonia"), "EDDL": ("Düsseldorf", "Düsseldorf", "Düsseldorf", "Düsseldorf"),
    "EDDH": ("Hambourg", "Hamburg", "Hamburg", "Hamburgo"), "EDDM": ("Munich", "Munich", "München", "Múnich"), "EDDF": ("Francfort", "Frankfurt", "Frankfurt", "Fráncfort"),
    "EDDB": ("Berlin", "Berlin", "Berlin", "Berlín"), "EDDS": ("Stuttgart", "Stuttgart", "Stuttgart", "Stuttgart"), "EDDN": ("Nuremberg", "Nuremberg", "Nürnberg", "Núremberg"),
    "EDDW": ("Brême", "Bremen", "Bremen", "Bremen"), "EDDP": ("Leipzig", "Leipzig", "Leipzig", "Leipzig"), "EDDC": ("Dresde", "Dresden", "Dresden", "Dresde"),
    "LEPA": ("Palma de Majorque", "Palma de Mallorca", "Palma de Mallorca", "Palma de Mallorca"), "LEMD": ("Madrid", "Madrid", "Madrid", "Madrid"), "LEBL": ("Barcelone", "Barcelona", "Barcelona", "Barcelona"),
    "LEAL": ("Alicante", "Alicante", "Alicante", "Alicante"), "LEMG": ("Malaga", "Malaga", "Malaga", "Málaga"), "LEZL": ("Séville", "Seville", "Sevilla", "Sevilla"),
    "GCTS": ("Ténérife", "Tenerife", "Teneriffa", "Tenerife"), "GCLP": ("Grande Canarie", "Gran Canaria", "Gran Canaria", "Gran Canaria"), "GCRR": ("Lanzarote", "Lanzarote", "Lanzarote", "Lanzarote"),
    "GCFV": ("Fuerteventura", "Fuerteventura", "Fuerteventura", "Fuerteventura"), "LPPT": ("Lisbonne", "Lisbon", "Lissabon", "Lisboa"), "LPPR": ("Porto", "Porto", "Porto", "Oporto"),
    "LPFR": ("Faro", "Faro", "Faro", "Faro"), "LIRF": ("Rome", "Rome", "Rom", "Roma"), "LIMC": ("Milan", "Milan", "Mailand", "Milán"), "LIPZ": ("Venise", "Venice", "Venedig", "Venecia"),
    "LIRN": ("Naples", "Naples", "Neapel", "Nápoles"), "LICC": ("Catane", "Catania", "Catania", "Catania"), "LGAV": ("Athènes", "Athens", "Athen", "Atenas"),
    "LGKR": ("Corfou", "Corfu", "Korfu", "Corfú"), "LGIR": ("Héraklion", "Heraklion", "Heraklion", "Heraclión"), "LTAI": ("Antalya", "Antalya", "Antalya", "Antalya"),
    "LTBJ": ("Izmir", "Izmir", "Izmir", "Esmirna"), "HEGN": ("Hurghada", "Hurghada", "Hurghada", "Hurgada"), "HESH": ("Charm el-Cheikh", "Sharm el-Sheikh", "Sharm el-Scheich", "Sharm el-Sheij"),
    "HELX": ("Louxor", "Luxor", "Luxor", "Luxor"), "HEMA": ("Marsa Alam", "Marsa Alam", "Marsa Alam", "Marsa Alam"), "GMMX": ("Marrakech", "Marrakech", "Marrakesch", "Marrakech"),
    "LFPG": ("Paris", "Paris", "Paris", "París"), "LFPO": ("Paris", "Paris", "Paris", "París"), "LFMN": ("Nice", "Nice", "Nizza", "Niza"), "LFLL": ("Lyon", "Lyon", "Lyon", "Lyon"),
    "LFML": ("Marseille", "Marseille", "Marseille", "Marsella"), "LFBO": ("Toulouse", "Toulouse", "Toulouse", "Toulouse"), "LFBD": ("Bordeaux", "Bordeaux", "Bordeaux", "Burdeos"),
    "LFRS": ("Nantes", "Nantes", "Nantes", "Nantes"), "LFLS": ("Grenoble", "Grenoble", "Grenoble", "Grenoble"), "LFLB": ("Chambéry", "Chambery", "Chambéry", "Chambery"),
    "LSZH": ("Zurich", "Zurich", "Zürich", "Zúrich"), "LSGG": ("Genève", "Geneva", "Genf", "Ginebra"), "LOWW": ("Vienne", "Vienna", "Wien", "Viena"),
    "LKPR": ("Prague", "Prague", "Prag", "Praga"), "LHBP": ("Budapest", "Budapest", "Budapest", "Budapest"), "EPWA": ("Varsovie", "Warsaw", "Warschau", "Varsovia"),
    "EHAM": ("Amsterdam", "Amsterdam", "Amsterdam", "Ámsterdam"), "EBBR": ("Bruxelles", "Brussels", "Brüssel", "Bruselas"), "EGLL": ("Londres", "London", "London", "Londres"),
    "EGKK": ("Londres", "London", "London", "Londres"), "EKCH": ("Copenhague", "Copenhagen", "Kopenhagen", "Copenhague"), "ESSA": ("Stockholm", "Stockholm", "Stockholm", "Estocolmo"),
    "ENGM": ("Oslo", "Oslo", "Oslo", "Oslo"), "EFHK": ("Helsinki", "Helsinki", "Helsinki", "Helsinki"), "LDDU": ("Dubrovnik", "Dubrovnik", "Dubrovnik", "Dubrovnik"),
    "LDSP": ("Split", "Split", "Split", "Split"), "LCLK": ("Larnaca", "Larnaca", "Larnaka", "Larnaca"), "LMML": ("Malte", "Malta", "Malta", "Malta"),
    "LROP": ("Bucarest", "Bucharest", "Bukarest", "Bucarest"), "LBSF": ("Sofia", "Sofia", "Sofia", "Sofía"), "OMDB": ("Dubaï", "Dubai", "Dubai", "Dubái"),
}
MOTS_AEROPORT = {"INTL", "INTERNATIONAL", "AIRPORT", "APT", "ARPT", "AIRFIELD", "AERODROME", "AEROPORT"}
LANGS = ("fr", "en", "de", "es")


def nom_ville(icao, nom):
    if icao in VILLES:
        v = VILLES[icao]
        return dict(zip(LANGS, v))
    n = (nom or icao).split("/")[0]
    mots = [m for m in re.split(r"\s+", n.strip()) if m.upper() not in MOTS_AEROPORT]
    v = " ".join(mots).title() or icao
    return {L: v for L in LANGS}


# ------------------------------------------------------------------ nombres et météo parlés
from num2words import num2words


def n_mot(n, lang):
    return num2words(int(n), lang=lang)


def vol_parle(fn):
    s = re.sub(r"\D", "", str(fn))
    out = {}
    if len(s) == 4:
        a, b = int(s[:2]), int(s[2:])
        for L in LANGS:
            na = n_mot(a, L)
            if b == 0:
                out[L] = na + {"fr": " cent", "en": " hundred", "de": "hundert", "es": " cien"}[L]
            elif b < 10:
                out[L] = na + {"fr": " zéro ", "en": " oh ", "de": " null ", "es": " cero "}[L] + n_mot(b, L)
            else:
                out[L] = na + " " + n_mot(b, L)
        return out
    return {L: " ".join(n_mot(int(c), L) for c in s) for L in LANGS}


def duree_parlee(sec):
    m = int(round(int(sec) / 300.0)) * 5          # arrondi à 5 minutes
    h, mi = divmod(m, 60)
    MIN_MOT = {"fr": "minutes", "en": "minutes", "de": "Minuten", "es": "minutos"}
    HEURE = {"fr": ("heure", "heures"), "en": ("hour", "hours"), "de": ("Stunde", "Stunden"), "es": ("hora", "horas")}
    out = {}
    for L in LANGS:
        if h == 0:
            out[L] = n_mot(mi, L) + " " + MIN_MOT[L]
            continue
        sing, plur = HEURE[L]
        if h == 1:
            # accord du "un" avec le genre feminin de l'unite (heure/Stunde/hora)
            UN_FEM = {"fr": "une", "de": "eine", "es": "una", "en": "one"}
            hf = UN_FEM[L] + " " + sing
        else:
            hf = n_mot(h, L) + " " + plur
        if mi == 0:
            out[L] = hf
        elif mi == 15:
            out[L] = hf + {"fr": " et quart", "en": " and fifteen minutes", "de": " und fünfzehn Minuten", "es": " y cuarto"}[L]
        elif mi == 30:
            out[L] = hf + {"fr": " et demie", "en": " and a half", "de": " und dreißig Minuten", "es": " y media"}[L]
        else:
            nm = n_mot(mi, L)
            out[L] = hf + {"fr": " " + nm, "en": " and " + nm + " minutes", "de": " und " + nm + " Minuten", "es": " y " + nm + " minutos"}[L]
    return out


def temp_parlee(t):
    if t is None:
        return {"fr": "une température agréable", "en": "a pleasant temperature",
                "de": "eine angenehme Temperatur", "es": "una temperatura agradable"}
    a = abs(t)
    DEG = {"fr": ("degré", "degrés"), "en": ("degree", "degrees"), "de": ("Grad", "Grad"), "es": ("grado", "grados")}
    MOINS = {"fr": "moins ", "en": "minus ", "de": "minus ", "es": "menos "}
    out = {}
    for L in LANGS:
        sing, plur = DEG[L]
        txt = n_mot(a, L) + " " + (sing if a == 1 else plur)
        out[L] = (MOINS[L] + txt) if t < 0 else txt
    return out


CARD = {
    "fr": ["nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest"],
    "en": ["northerly", "north-easterly", "easterly", "south-easterly", "southerly", "south-westerly", "westerly", "north-westerly"],
    "de": ["Nord", "Nordost", "Ost", "Südost", "Süd", "Südwest", "West", "Nordwest"],
    "es": ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"],
}


def parse_metar(m):
    r = {"temp": None, "wd": None, "kt": 0, "sky": "clr", "wx": []}
    if not m:
        return r
    core = re.split(r"\b(TEMPO|BECMG|NOSIG)\b", m)[0]
    t = re.search(r"\s(M?\d{2})/(M?\d{2})\b", core)
    if t:
        v = t.group(1)
        r["temp"] = -int(v[1:]) if v.startswith("M") else int(v)
    w = re.search(r"\s(VRB|\d{3})(\d{2,3})(?:G\d{2,3})?KT", core)
    if w:
        r["wd"] = None if w.group(1) == "VRB" else int(w.group(1))
        r["kt"] = int(w.group(2))
    rang = {"FEW": 1, "SCT": 2, "BKN": 3, "OVC": 4}
    best = 0
    for lay in re.findall(r"\b(FEW|SCT|BKN|OVC)\d{3}", core):
        best = max(best, rang[lay])
    r["sky"] = ["clr", "few", "sct", "bkn", "ovc"][best]
    for tok in core.split():
        mm = re.match(r"^[-+]?(?:VC)?(TS|SH)?(RA|SN|DZ|GR|FG|BR|HZ)$", tok)
        if mm:
            r["wx"].append(mm.group(2) if not mm.group(1) else mm.group(1))
        elif tok in ("TS", "-TSRA", "TSRA", "+TSRA"):
            r["wx"].append("TS")
    return r


def ciel_parle(m):
    S = {"clr": {"fr": "ciel dégagé", "en": "clear skies", "de": "klarer Himmel", "es": "cielo despejado"},
         "few": {"fr": "quelques nuages", "en": "a few clouds", "de": "ein paar Wolken", "es": "algunas nubes"},
         "sct": {"fr": "quelques nuages épars", "en": "scattered clouds", "de": "aufgelockerte Bewölkung", "es": "nubes dispersas"},
         "bkn": {"fr": "ciel nuageux", "en": "cloudy skies", "de": "bewölkter Himmel", "es": "cielo nublado"},
         "ovc": {"fr": "ciel couvert", "en": "overcast skies", "de": "bedeckter Himmel", "es": "cielo cubierto"}}[m["sky"]]
    WX = {"RA": {"fr": "de la pluie", "en": "rain", "de": "Regen", "es": "lluvia"},
          "SN": {"fr": "de la neige", "en": "snow", "de": "Schnee", "es": "nieve"},
          "DZ": {"fr": "de la bruine", "en": "drizzle", "de": "Nieselregen", "es": "llovizna"},
          "FG": {"fr": "du brouillard", "en": "fog", "de": "Nebel", "es": "niebla"},
          "BR": {"fr": "de la brume", "en": "mist", "de": "Dunst", "es": "neblina"},
          "TS": {"fr": "des orages", "en": "thunderstorms", "de": "Gewitter", "es": "tormentas"},
          "GR": {"fr": "de la grêle", "en": "hail", "de": "Hagel", "es": "granizo"},
          "HZ": {"fr": "une légère brume sèche", "en": "haze", "de": "Dunstschleier", "es": "calima"}}
    AVEC = {"fr": ", avec ", "en": ", with ", "de": ", mit ", "es": ", con "}
    for k in ("TS", "SN", "RA", "DZ", "FG", "BR", "GR", "HZ"):
        if k in m["wx"]:
            return {L: S[L] + AVEC[L] + WX[k][L] for L in LANGS}
    return dict(S)


def vent_parle(m):
    """Vent exprime de facon qualitative : la vitesse en noeuds etait mal
    prononcee par la synthese vocale, donc plus de chiffres ici, juste une
    appreciation (pas de vent / un peu de vent / du vent / beaucoup de vent)
    adaptee au seuil reel. Le texte renvoye inclut sa propre ponctuation de
    liaison (", ..."), a inserer directement apres {TEMP_D} dans les annonces."""
    kt = m["kt"]
    if kt <= 3:
        return {"fr": ", sans vent", "en": ", there is no wind",
                "de": ", es gibt keinen Wind", "es": ", no hay viento"}
    if kt <= 10:
        return {"fr": ", avec un peu de vent", "en": ", there is a bit of wind",
                "de": ", es gibt etwas Wind", "es": ", hay un poco de viento"}
    if kt <= 20:
        return {"fr": ", avec du vent", "en": ", there is some wind",
                "de": ", es gibt Wind", "es": ", hay viento"}
    return {"fr": ", avec beaucoup de vent, soyez prudents",
            "en": ", watch out, there is a lot of wind",
            "de": ", Achtung, es gibt viel Wind",
            "es": ", atención, hay mucho viento"}


def commentaire(m):
    t = m["temp"]
    if any(k in m["wx"] for k in ("RA", "DZ", "TS", "SH")):
        return {"fr": "Pensez au parapluie.", "en": "Don't forget your umbrella.",
                "de": "Denken Sie an Ihren Regenschirm.", "es": "No olvide el paraguas."}
    if t is None:
        return {"fr": "", "en": "", "de": "", "es": ""}
    if t >= 30:
        return {"fr": "Pensez à la crème solaire.", "en": "Don't forget the sunscreen.",
                "de": "Denken Sie an Sonnencreme.", "es": "No olvide la crema solar."}
    if t >= 22:
        return {"fr": "Le temps est idéal pour une terrasse.", "en": "Perfect weather for a terrace.",
                "de": "Ideales Wetter für eine Terrasse.", "es": "Un tiempo perfecto para una terraza."}
    if t >= 12:
        return {"fr": "Un temps tout à fait raisonnable.", "en": "A perfectly reasonable climate.",
                "de": "Ein ganz angenehmes Wetter.", "es": "Un clima bastante agradable."}
    if t >= 3:
        return {"fr": "Gardez votre manteau à portée de main.", "en": "Keep your coat within reach.",
                "de": "Halten Sie Ihren Mantel griffbereit.", "es": "Tenga el abrigo a mano."}
    return {"fr": "Il fait frisquet, couvrez-vous bien.", "en": "It is chilly, so wrap up warm.",
            "de": "Es ist frisch, ziehen Sie sich warm an.", "es": "Hace fresco, abríguese bien."}


def turbulence_parle(plan):
    """Estimation grossiere a partir des sigmets actifs et du cisaillement (shear) par point de la navlog
    SimBrief brute (pas une prevision precise, juste de quoi rassurer ou prevenir les passagers)."""
    FORT = {"fr": "Le commandant de bord annonce quelques turbulences possibles en cours de route. Gardez votre ceinture attachée par précaution.",
            "en": "The captain expects some turbulence along the way. Please keep your seat belt fastened as a precaution.",
            "de": "Der Kapitän rechnet unterwegs mit möglichen Turbulenzen. Bitte behalten Sie zur Vorsicht Ihren Sicherheitsgurt angelegt.",
            "es": "El comandante prevé algunas turbulencias durante el vuelo. Por precaución, mantenga el cinturón abrochado."}
    LEGER = {"fr": "De légères turbulences sont possibles durant le vol, rien d'inquiétant.",
             "en": "Some light turbulence is possible during the flight, nothing to worry about.",
             "de": "Leichte Turbulenzen sind während des Flugs möglich, kein Grund zur Sorge.",
             "es": "Es posible que haya ligeras turbulencias durante el vuelo, sin motivo de preocupación."}
    CALME = {"fr": "Le vol devrait se dérouler sans turbulence notable.",
             "en": "The flight should be smooth, with no significant turbulence expected.",
             "de": "Der Flug sollte ruhig verlaufen, ohne nennenswerte Turbulenzen.",
             "es": "El vuelo debería transcurrir sin turbulencias significativas."}
    sig = (plan.get("sigmets") or {}).get("sigmet")
    if isinstance(sig, dict):
        sig = [sig]
    elif not isinstance(sig, list):
        sig = []
    for s in sig:
        if str(s.get("hazard", "")).upper() in ("TURB", "CAT"):
            return dict(FORT)
    nav = (plan.get("navlog") or {}).get("fix") or []
    if isinstance(nav, dict):
        nav = [nav]
    pics = []
    for x in nav:
        try: pics.append(int(float(x.get("shear", 0) or 0)))
        except Exception: pass
    mx = max(pics) if pics else 0
    if mx >= 4:
        return dict(FORT)
    if mx >= 2:
        return dict(LEGER)
    return dict(CALME)


def salut_fin_service_par_langue():
    """Salutation de fin de service (bonne journee / bonne soiree / bon
    week-end), choisie selon l'heure et le jour REELS (poste de l'equipage,
    pas l'heure simulee du vol). Reutilisee a la fois pour les annonces
    cabine pre-enregistrees (DeboardingComplete) et pour le message en
    direct au commandant en fin de debarquement (voir surveillance_gsx)."""
    lt = time.localtime()
    heure_reelle, jour_semaine = lt.tm_hour, lt.tm_wday  # 0=lundi ... 6=dimanche
    weekend_proche = (jour_semaine == 4 and heure_reelle >= 16) or jour_semaine in (5, 6)
    if weekend_proche:
        cle = "weekend"
    elif heure_reelle < 18:
        cle = "journee"
    else:
        cle = "soiree"
    return {
        "journee": {"fr": "bonne journée", "en": "have a good day", "de": "einen schönen Tag", "es": "que tengan un buen día"},
        "soiree": {"fr": "bonne soirée", "en": "have a good evening", "de": "einen schönen Abend", "es": "buenas tardes"},
        "weekend": {"fr": "bon week-end", "en": "have a great weekend", "de": "ein schönes Wochenende", "es": "buen fin de semana"},
    }[cle]


# Corrections de prononciation pour des noms de compagnie connus pour mal
# passer en synthese vocale une fois le nom colle sans espace (ex : le champ
# "atc_airline" d'une livree Fenix contient souvent "AirFrance" plutot que
# "Air France", ce qui fait perdre la fin du mot - certaines voix lisent le
# bloc comme un sigle et avalent la derniere syllabe). Cle = nom normalise
# (minuscules, espaces retires) tel qu'il peut arriver depuis la livree ou
# la configuration ; valeur = graphie correcte a utiliser dans les annonces.
CORRECTIONS_PRONONCIATION_COMPAGNIE = {
    "airfrance": "Air France",
    "eurowings": "Eurowingss",
    "eurowingseurope": "Eurowingss Europe",
    "airnewzealand": "Air New Zealand",
    "airchina": "Air China",
    "airindia": "Air India",
    "airindiaexpress": "Air India Express",
    "airserbia": "Air Serbia",
    "aircanada": "Air Canada",
    "aircairo": "Air Cairo",
    "aircorsica": "Air Corsica",
    "britishairways": "British Airways",
    "britishmidland": "British Midland",
    "bmibritishmidland": "Bmi British Midland",
    "brusselsairlines": "Brussels Airlines",
    "bulgariaairlines": "Bulgaria Airlines",
    "bulgariaair": "Bulgaria Air",
    "cathaydragon": "Cathay Dragone",
    "cebupacificair": "Cebu Pacific Air",
    "chinaeastern": "China Eastern",
    "chinaexpress": "China Express",
    "chinasouthern": "China Southeurne",
    "croatiaairlines": "Croatia Airlines",
    "cyprusairways": "Cyprus Airways",
    "deltaairlines": "Delta Air Lines",
    "discoverairlines": "Discover Airlines",
    "easyjet": "easyJet",
    "easyjeteurope": "easyJet Europe",
    "easyjetswitzerland": "easyJet Switzerland",
    "egyptair": "Egypt Air",
    "etihadairways": "Etihad Airways",
    "finnair": "Finnair",
    "frontierairlines": "Frontier Airlines",
    "germanwings": "Germane Wingss",
    "hongkongairlines": "Hong Kong Airlines",
    "hkexpress": "HK Express",
    "iberiaexpress": "Iberia Express",
    "iranair": "Iran Air",
    "iraqiairways": "Iraqi Airways",
    "itaairways": "ITA Airways",
    "jazeeraairways": "Jazeera Airways",
    "middleeastairlines": "Middle East Airlines",
    "nileair": "Nile Air",
    "northwestairlines": "Northwest Airlines",
    "qatarairways": "Qatar Airways",
    "s7airlines": "S7 Airlines",
    "saudiarabianairlines": "Saudi Arabian Airlines",
    "southafricanairways": "South African Airways",
    "spiritairlines": "Spirit Airlines",
    "swiss": "Swiss",
    "syrianair": "Syrian Air",
    "thaiairways": "Thai Airways",
    "titanairways": "Titan Airways",
    "turkishairlines": "Turkish Airlines",
    "unitedairlines": "United Airlines",
    "uralairlines": "Ural Airlines",
    "usairways": "US Airways",
    "uzbekistanairways": "Uzbekistan Airways",
    "virginamerica": "Virgin America",
    "virginatlanticairways": "Virgin Atlantic Airways",
    "whiteairways": "White Airways",
    "wizzair": "Wizz Air",

    # --- corrections demandees apres ecoute du 1er lot d'echantillons (22/11/2026) ---
    # compagnies "Jet..." : forcer le "t" final de Jet (prononce a l'anglaise,
    # pas "je" muet comme en francais) + le reste a l'anglaise.
    "jetblue": "Djette Bloue",
    "jetstar": "Djette Star",
    "jetstarasia": "Djette Star Asia",
    "jetstarjapan": "Djette Star Japan",
    "canadajetlines": "Canada Djette Laïnz",
    "getjet": "Djette Djette",
    "monarchairlines": "Monark Airlines",
    "nouvelair": "Nouvel Air",
    "qantaslink": "Quantass Link",
    "royaljordanian": "Royal Djordanian",
    "sichuanairlines": "Sichuane Airlines",
    "solomon": "Solomone",
    "srilankan": "Sri Lanka",
    "stareast": "Stahr East",
    "sundair": "Sunne Dair",
    "tapairportugal": "T. A. P. Air Portugal",
    "tigerair": "Tigue Air",
    "tuiflynetherlands": "TUI fly Neverlands",
    "vivaaerobus": "Viva Aerobuss",
    "allleisureairways": "All Leisure, Airways",
    "allegiantair": "Allegiante Air",
    "animawings": "Animawingss",
    "austrian": "Austriane",
    "baeuroflyer": "BA Euro Flaïeur",
    "caledonianairways": "Calédonian Airways",
    "citilink": "Citi Link",
    "eurofly": "Euro Flaï",
    "evaair": "Eva Air",
    "flyadeal": "Fly euh Dîle",
    "flynas": "Flaï Nasse",
    "flyniki": "Flaï Niki",
    "iberworldairlines": "Iber Oueurld Airlines",
    # virgule pour empecher la liaison/fusion "vol ANA" -> "volana"
    "ana": ", ANA",
}

# ------------------------------------------------------------------ services a bord par compagnie
# Bibliotheque de phrases d'annonce reprenant le VRAI service a bord (restauration,
# wifi/divertissement, programme de fidelite...) compagnie par compagnie, identifiee
# automatiquement par la livree active (meme cle que CORRECTIONS_PRONONCIATION_COMPAGNIE,
# normalisee via re.sub(r"[^a-z0-9]", "", nom.lower())).
#
# Regle volontaire : on ne cite JAMAIS les noms commerciaux de services/programmes
# (ex. pas de "Wings Bistro", "Wings Connect", "FlyNet", "High Life Cafe", "Avios",
# "Miles & More", "SAFt", "Meal Deal"...) car la synthese vocale les retranscrit
# souvent mal. Seuls les vrais noms de plats/produits (langage courant, ex. "Butter
# Chicken", "wrap", "croque-monsieur") sont repris tels quels.
#
# Une seule phrase est piochee au hasard par generation (cf. contexte()) : on ne
# recite jamais tout le service d'un coup, exactement comme pour Eurowings.
SERVICES_BORD = {
    "eurowings": {
        "wifi": {
            "fr": " Pour patienter, une connexion Wi-Fi et un programme de divertissement sont proposés en option, directement depuis votre propre appareil.",
            "en": " To keep you entertained, a Wi-Fi connection and an entertainment programme are available as a paid option, straight from your own device.",
            "de": " Zu Ihrer Unterhaltung bieten wir Ihnen optional eine WLAN-Verbindung und ein Unterhaltungsprogramm direkt auf Ihrem eigenen Gerät an.",
            "es": " Para su entretenimiento, ofrecemos opcionalmente una conexión Wi-Fi y un programa de entretenimiento directamente desde su propio dispositivo.",
        },
        "annonces": [
            {"fr": "Notre équipage vous propose un menu complet avec un plat, une boisson et un dessert, à prix avantageux.",
             "en": "Our crew offers a complete meal deal with a dish, a drink and a dessert, at a great price.",
             "de": "Unsere Crew bietet Ihnen ein komplettes Menü mit Gericht, Getränk und Dessert zu einem attraktiven Preis.",
             "es": "Nuestra tripulación les ofrece un menú completo con un plato, una bebida y un postre, a un precio ventajoso."},
            {"fr": "Notre carte propose entre autres un döner au poulet mariné, des frites, ou un butter chicken au riz basmati.",
             "en": "Our menu includes a marinated chicken döner, fries, or a butter chicken with basmati rice.",
             "de": "Unsere Karte bietet unter anderem einen Döner mit mariniertem Hähnchen, Pommes, oder ein Butter Chicken mit Basmatireis.",
             "es": "Nuestra carta incluye entre otros un döner de pollo marinado, patatas fritas, o un butter chicken con arroz basmati."},
            {"fr": "Pour rappel, le règlement à bord se fait uniquement par carte bancaire ou paiement sans contact.",
             "en": "Please note that payment on board is by card or contactless only.",
             "de": "Bitte beachten Sie, dass die Zahlung an Bord nur per Karte oder kontaktlos möglich ist.",
             "es": "Recuerden que el pago a bordo se realiza únicamente con tarjeta o sin contacto."},
            {"fr": "Petite astuce : apportez votre propre tasse réutilisable, et bénéficiez d'une réduction sur une boisson chaude.",
             "en": "A small tip: bring your own reusable cup, and get a discount on a hot drink.",
             "de": "Ein kleiner Tipp: Bringen Sie Ihre eigene wiederverwendbare Tasse mit, und erhalten Sie einen Rabatt auf ein heißes Getränk.",
             "es": "Un pequeño consejo: traigan su propia taza reutilizable, y obtengan un descuento en una bebida caliente."},
            {"fr": "Pour les voyageurs sensibles à l'environnement, notre carte propose aussi une contribution volontaire au carburant durable.",
             "en": "For environmentally-minded travellers, our menu also offers a voluntary contribution towards sustainable fuel.",
             "de": "Für umweltbewusste Reisende bietet unsere Karte auch einen freiwilligen Beitrag zu nachhaltigem Treibstoff.",
             "es": "Para los viajeros sensibles al medio ambiente, nuestra carta también ofrece una contribución voluntaria al combustible sostenible."},
            {"fr": "En cette fin de journée, notre équipage vous propose aussi une offre apéritive, bière et snack salé à prix réduit.",
             "en": "At this time of day, our crew also offers an evening deal, a beer and a savoury snack at a reduced price.",
             "de": "Zu dieser Tageszeit bietet Ihnen unsere Crew auch ein Feierabend-Angebot: ein Bier und einen herzhaften Snack zum reduzierten Preis.",
             "es": "A esta hora del día, nuestra tripulación también ofrece una oferta de tarde: una cerveza y un tentempié salado a precio reducido."},
            {"fr": "Pensez à consulter notre magazine de bord, glissé dans la pochette devant vous, pour découvrir nos destinations.",
             "en": "Feel free to browse our in-flight magazine, tucked in the seat pocket in front of you, to discover our destinations.",
             "de": "Werfen Sie gerne einen Blick in unser Bordmagazin in der Sitztasche vor Ihnen, und entdecken Sie unsere Reiseziele.",
             "es": "No duden en consultar nuestra revista de a bordo, en el bolsillo del asiento delante de ustedes, para descubrir nuestros destinos."},
        ],
    },
    "transavia": {
        "annonces": [
            {"fr": "Pour bien commencer la journée, notre carte propose une offre petit-déjeuner avec jus d'orange, viennoiserie et café, à prix avantageux.",
             "en": "To start the day well, our menu offers a breakfast deal with orange juice, pastry and coffee, at a great price.",
             "de": "Für einen guten Start in den Tag bietet unsere Karte ein Frühstücksangebot mit Orangensaft, Gebäck und Kaffee zu einem attraktiven Preis.",
             "es": "Para empezar bien el día, nuestra carta ofrece una oferta de desayuno con zumo de naranja, bollería y café, a un precio ventajoso."},
            {"fr": "Petite faim ? Notre offre salée réunit un wrap, un soda et des chips pour une pause gourmande.",
             "en": "Feeling peckish? Our savoury deal brings together a wrap, a soda and some chips for a tasty break.",
             "de": "Kleiner Hunger? Unser herzhaftes Angebot vereint einen Wrap, ein Softdrink und Chips für eine leckere Pause.",
             "es": "¿Un poco de hambre? Nuestra oferta salada reúne un wrap, un refresco y patatas fritas para una pausa gourmet."},
            {"fr": "Notre carte propose entre autres une pizza margarita, un croque-monsieur, ou un wrap au poulet.",
             "en": "Our menu includes a margherita pizza, a ham and cheese toastie, or a chicken wrap.",
             "de": "Unsere Karte bietet unter anderem eine Pizza Margherita, einen Toast mit Schinken und Käse, oder einen Wrap mit Hähnchen.",
             "es": "Nuestra carta incluye entre otros una pizza margarita, un sándwich mixto, o un wrap de pollo."},
            {"fr": "Pensez-y : à partir de plusieurs articles achetés sur notre carte, une remise s'applique automatiquement.",
             "en": "Worth knowing: buy several items from our menu and a discount is applied automatically.",
             "de": "Zur Erinnerung: Ab mehreren gekauften Artikeln unserer Karte wird automatisch ein Rabatt gewährt.",
             "es": "Para tener en cuenta: a partir de varios artículos comprados en nuestra carta, se aplica un descuento automáticamente."},
            {"fr": "Notre carte met à l'honneur des producteurs français, du café aux madeleines, en passant par nos vins certifiés agriculture durable.",
             "en": "Our menu highlights French producers, from coffee to madeleines, including our sustainably certified wines.",
             "de": "Unsere Karte würdigt französische Erzeuger, vom Kaffee bis zu den Madeleines, sowie unsere nachhaltig zertifizierten Weine.",
             "es": "Nuestra carta destaca a productores franceses, desde el café hasta las madalenas, incluyendo nuestros vinos con certificación sostenible."},
            {"fr": "Le règlement à bord est accepté par carte, sans contact, ou en espèces.",
             "en": "Payment on board is accepted by card, contactless, or cash.",
             "de": "Die Zahlung an Bord wird per Karte, kontaktlos, oder in bar akzeptiert.",
             "es": "El pago a bordo se acepta con tarjeta, sin contacto, o en efectivo."},
            {"fr": "Pour les envies shopping, notre catalogue boutique est disponible dans la pochette de votre siège.",
             "en": "For some shopping, our boutique catalogue is available in your seat pocket.",
             "de": "Für Shopping-Lust liegt unser Boutique-Katalog in Ihrer Sitztasche bereit.",
             "es": "Para los que quieran ir de compras, nuestro catálogo de tienda está disponible en el bolsillo de su asiento."},
            {"fr": "Pour accompagner la fin de votre vol, découvrez nos cocktails et vins à bord.",
             "en": "To round off your flight, discover our cocktails and wines on board.",
             "de": "Zum Ausklang Ihres Fluges entdecken Sie unsere Cocktails und Weine an Bord.",
             "es": "Para acompañar el final de su vuelo, descubran nuestros cócteles y vinos a bordo."},
        ],
    },
    "airfrance": {
        "annonces": [
            {"fr": "Notre équipage va maintenant débuter le service repas ; nous vous proposerons un choix entre plusieurs menus.",
             "en": "Our crew will now begin the meal service; we will offer you a choice between several menus.",
             "de": "Unsere Crew beginnt nun mit dem Essensservice; wir bieten Ihnen die Wahl zwischen mehreren Menüs.",
             "es": "Nuestra tripulación va a comenzar ahora el servicio de comida; les propondremos elegir entre varios menús."},
            {"fr": "Sur nos vols long-courriers, du champagne est proposé pendant le service, quelle que soit la cabine.",
             "en": "On our long-haul flights, champagne is offered during the service, whatever your cabin.",
             "de": "Auf unseren Langstreckenflügen wird während des Service Champagner angeboten, unabhängig von der Kabine.",
             "es": "En nuestros vuelos de largo recorrido, se ofrece champán durante el servicio, sea cual sea la cabina."},
            {"fr": "Nos repas sont élaborés avec des produits frais et de saison, originaires de producteurs français.",
             "en": "Our meals are prepared with fresh, seasonal products, sourced from French producers.",
             "de": "Unsere Mahlzeiten werden mit frischen, saisonalen Produkten von französischen Erzeugern zubereitet.",
             "es": "Nuestras comidas se elaboran con productos frescos y de temporada, procedentes de productores franceses."},
            {"fr": "Une option végétarienne est disponible pour l'ensemble de nos repas ; n'hésitez pas à la demander à notre équipage.",
             "en": "A vegetarian option is available for all our meals; feel free to ask our crew.",
             "de": "Für alle unsere Mahlzeiten ist eine vegetarische Option erhältlich; fragen Sie gerne unsere Crew.",
             "es": "Hay disponible una opción vegetariana para todas nuestras comidas; no duden en pedirla a nuestra tripulación."},
            {"fr": "Un menu spécialement conçu pour les enfants est disponible sur demande auprès de notre équipage.",
             "en": "A menu specially designed for children is available on request from our crew.",
             "de": "Ein speziell für Kinder konzipiertes Menü ist auf Anfrage bei unserer Crew erhältlich.",
             "es": "Hay disponible, previa solicitud a nuestra tripulación, un menú especialmente concebido para niños."},
            {"fr": "Dans quelques instants, votre repas vous sera servi avec le plus grand soin, à la française.",
             "en": "In a few moments, your meal will be served to you with the greatest care, in French style.",
             "de": "In Kürze wird Ihnen Ihre Mahlzeit mit größter Sorgfalt, auf französische Art, serviert.",
             "es": "En unos instantes, se les servirá su comida con el mayor esmero, al estilo francés."},
        ],
    },
    "lufthansa": {
        "annonces": [
            {"fr": "Notre équipage va vous servir une boisson et une petite douceur sucrée, offertes à bord.",
             "en": "Our crew will serve you a drink and a little sweet treat, both complimentary on board.",
             "de": "Unsere Crew serviert Ihnen ein Getränk und eine kleine Süßigkeit, beides an Bord inklusive.",
             "es": "Nuestra tripulación les servirá una bebida y un pequeño dulce, ambos incluidos a bordo."},
            {"fr": "En complément, un encas salé vous sera également proposé pendant ce service.",
             "en": "In addition, a savoury snack will also be offered during this service.",
             "de": "Ergänzend wird Ihnen während dieses Service auch ein herzhafter Snack angeboten.",
             "es": "Además, también se les ofrecerá un tentempié salado durante este servicio."},
            {"fr": "Le repas chaud sera servi sous peu, avec le choix entre deux plats.",
             "en": "The hot meal will be served shortly, with a choice between two dishes.",
             "de": "Die warme Mahlzeit wird in Kürze serviert, mit der Wahl zwischen zwei Gerichten.",
             "es": "La comida caliente se servirá en breve, con opción a elegir entre dos platos."},
            {"fr": "Les passagers ayant précommandé un menu spécial seront servis en priorité.",
             "en": "Passengers who pre-ordered a special menu will be served first.",
             "de": "Fluggäste, die ein Sondermenü vorbestellt haben, werden zuerst bedient.",
             "es": "Los pasajeros que hayan reservado previamente un menú especial serán atendidos en primer lugar."},
            {"fr": "Pour rester joignable pendant le vol, une messagerie Wi-Fi est accessible gratuitement sur votre appareil.",
             "en": "To stay reachable during the flight, a free messaging Wi-Fi service is available on your device.",
             "de": "Um während des Fluges erreichbar zu bleiben, steht Ihnen kostenlos ein WLAN-Nachrichtendienst auf Ihrem Gerät zur Verfügung.",
             "es": "Para seguir localizables durante el vuelo, disponen gratuitamente de un servicio Wi-Fi de mensajería en su dispositivo."},
            {"fr": "Pour une connexion complète, une offre Wi-Fi est également disponible en option à bord.",
             "en": "For full connectivity, a Wi-Fi package is also available as an option on board.",
             "de": "Für eine vollständige Verbindung ist an Bord zudem optional ein WLAN-Paket erhältlich.",
             "es": "Para una conexión completa, también hay disponible a bordo un paquete Wi-Fi opcional."},
            {"fr": "Notre presse numérique ainsi que notre programme de divertissement sont accessibles depuis votre écran ou votre appareil.",
             "en": "Our digital press as well as our entertainment programme are accessible from your screen or your own device.",
             "de": "Unsere digitale Presse sowie unser Unterhaltungsprogramm sind über Ihren Bildschirm oder Ihr eigenes Gerät zugänglich.",
             "es": "Nuestra prensa digital, así como nuestro programa de entretenimiento, son accesibles desde su pantalla o su propio dispositivo."},
            {"fr": "Un menu enfant est disponible sur ce vol pour nos plus jeunes passagers.",
             "en": "A children's menu is available on this flight for our youngest passengers.",
             "de": "Für unsere jüngsten Fluggäste steht auf diesem Flug ein Kindermenü zur Verfügung.",
             "es": "En este vuelo hay disponible un menú infantil para nuestros pasajeros más pequeños."},
        ],
    },
    "britishairways": {
        "annonces": [
            {"fr": "Notre carte à bord propose une sélection de sandwichs, friandises et boissons chaudes ou froides, disponible dès à présent.",
             "en": "Our on-board menu offers a selection of sandwiches, treats and hot or cold drinks, available right now.",
             "de": "Unsere Bordkarte bietet eine Auswahl an Sandwiches, Süßigkeiten und warmen oder kalten Getränken, ab sofort erhältlich.",
             "es": "Nuestra carta a bordo ofrece una selección de sándwiches, dulces y bebidas calientes o frías, disponible desde ahora."},
            {"fr": "Pour gagner du temps à bord, pensez à précommander vos produits préférés en ligne avant votre prochain vol.",
             "en": "To save time on board, remember to pre-order your favourite items online before your next flight.",
             "de": "Um an Bord Zeit zu sparen, denken Sie daran, Ihre Lieblingsprodukte vor Ihrem nächsten Flug online vorzubestellen.",
             "es": "Para ganar tiempo a bordo, recuerden pedir por anticipado en línea sus productos favoritos antes de su próximo vuelo."},
            {"fr": "Nos passagers en classe affaires bénéficient d'un repas inclus, préparé avec des ingrédients de saison et des produits britanniques.",
             "en": "Our business class passengers enjoy an included meal, prepared with seasonal ingredients and British produce.",
             "de": "Unsere Business-Class-Passagiere erhalten eine inkludierte Mahlzeit, zubereitet mit saisonalen Zutaten und britischen Produkten.",
             "es": "Nuestros pasajeros de clase ejecutiva disfrutan de una comida incluida, preparada con ingredientes de temporada y productos británicos."},
            {"fr": "Chaque achat à bord vous permet de cumuler des points de fidélité, utilisables pour vos prochains vols.",
             "en": "Every purchase on board earns you loyalty points, which can be used for your future flights.",
             "de": "Jeder Einkauf an Bord bringt Ihnen Treuepunkte ein, die Sie für Ihre nächsten Flüge nutzen können.",
             "es": "Cada compra a bordo les permite acumular puntos de fidelidad, utilizables para sus próximos vuelos."},
            {"fr": "Un forfait de messagerie Wi-Fi est disponible à bord dès les premières minutes du vol.",
             "en": "A messaging Wi-Fi package is available on board from the first few minutes of the flight.",
             "de": "Ein WLAN-Nachrichtenpaket ist an Bord bereits ab den ersten Flugminuten verfügbar.",
             "es": "Un paquete Wi-Fi de mensajería está disponible a bordo desde los primeros minutos del vuelo."},
            {"fr": "Pour naviguer ou regarder des films pendant le vol, un forfait Wi-Fi complet est proposé en option.",
             "en": "To browse or watch films during the flight, a full Wi-Fi package is offered as an option.",
             "de": "Um während des Fluges zu surfen oder Filme zu sehen, wird optional ein vollständiges WLAN-Paket angeboten.",
             "es": "Para navegar o ver películas durante el vuelo, se ofrece opcionalmente un paquete Wi-Fi completo."},
            {"fr": "Une petite bouteille d'eau et un en-cas vous seront offerts au cours de ce vol.",
             "en": "A small bottle of water and a snack will be offered to you during this flight.",
             "de": "Während dieses Fluges erhalten Sie eine kleine Flasche Wasser und einen Snack.",
             "es": "Durante este vuelo se les ofrecerá una pequeña botella de agua y un tentempié."},
        ],
    },
    "easyjet": {
        "annonces": [
            {"fr": "Notre équipage va maintenant passer avec le chariot de restauration : sandwichs, snacks sucrés et salés, boissons chaudes et froides.",
             "en": "Our crew will now be passing through the cabin with the trolley: sandwiches, sweet and savoury snacks, hot and cold drinks.",
             "de": "Unsere Crew kommt nun mit dem Bordwagen durch die Kabine: Sandwiches, süße und herzhafte Snacks, warme und kalte Getränke.",
             "es": "Nuestra tripulación pasará ahora con el carrito: sándwiches, snacks dulces y salados, bebidas calientes y frías."},
            {"fr": "Notre carte propose entre autres des chips, du chocolat, ainsi qu'un choix de thé, café ou chocolat chaud.",
             "en": "Our menu includes crisps, chocolate, as well as a choice of tea, coffee or hot chocolate.",
             "de": "Unsere Karte bietet unter anderem Chips, Schokolade, sowie eine Auswahl an Tee, Kaffee oder heißer Schokolade.",
             "es": "Nuestra carta incluye entre otros patatas fritas, chocolate, así como una selección de té, café o chocolate caliente."},
            {"fr": "En cette fin de journée, une bière, un gin tonic ou un verre de vin vous seront proposés pour accompagner votre vol.",
             "en": "At this time of day, a beer, a gin and tonic or a glass of wine will be on offer to accompany your flight.",
             "de": "Zu dieser Tageszeit werden Ihnen ein Bier, ein Gin Tonic oder ein Glas Wein angeboten, um Ihren Flug zu begleiten.",
             "es": "A esta hora del día, se les ofrecerá una cerveza, un gin-tonic o una copa de vino para acompañar su vuelo."},
            {"fr": "Le règlement à bord se fait uniquement par carte bancaire ou paiement sans contact, les espèces ne sont pas acceptées.",
             "en": "Payment on board is by card or contactless only, cash is not accepted.",
             "de": "Die Zahlung an Bord erfolgt nur per Karte oder kontaktlos, Bargeld wird nicht akzeptiert.",
             "es": "El pago a bordo se realiza únicamente con tarjeta o sin contacto, no se acepta efectivo."},
            {"fr": "Notre sélection boutique à bord propose parfums, cosmétiques et articles de voyage, à retrouver dans notre catalogue.",
             "en": "Our on-board boutique selection offers perfumes, cosmetics and travel accessories, available in our catalogue.",
             "de": "Unsere Bordboutique bietet Parfums, Kosmetika und Reisezubehör, die Sie in unserem Katalog finden.",
             "es": "Nuestra selección de tienda a bordo ofrece perfumes, cosméticos y artículos de viaje, disponibles en nuestro catálogo."},
            {"fr": "Pour les voyages en famille, un menu composé d'une collation sucrée et d'une boisson est disponible pour les enfants.",
             "en": "For families travelling together, a menu made up of a sweet snack and a drink is available for children.",
             "de": "Für Familien mit Kindern ist ein Menü aus einem süßen Snack und einem Getränk für Kinder erhältlich.",
             "es": "Para las familias que viajan juntas, hay disponible para los niños un menú compuesto por un tentempié dulce y una bebida."},
            {"fr": "Pensez à réserver vos repas à l'avance lors de votre prochaine réservation, pour profiter de tarifs préférentiels.",
             "en": "Remember to pre-book your meals when making your next booking, to enjoy preferential rates.",
             "de": "Denken Sie daran, Ihre Mahlzeiten bei Ihrer nächsten Buchung vorzubestellen, um von Vorzugspreisen zu profitieren.",
             "es": "Recuerden reservar sus comidas por adelantado en su próxima reserva, para disfrutar de tarifas preferentes."},
        ],
    },
}


def embellir_nom_compagnie(nom):
    """Rend un nom de compagnie correctement prononcable par la synthese
    vocale, quelle que soit la langue : d'abord une correspondance exacte
    dans CORRECTIONS_PRONONCIATION_COMPAGNIE (compagnies connues pour mal
    passer telles quelles), sinon une separation automatique des mots colles
    ("AirFrance" -> "Air France", "KLMRoyalDutch" -> "KLM Royal Dutch"),
    pour que chaque voix (francais, anglais, allemand, espagnol) lise de
    vrais mots plutot qu'un bloc illisible."""
    if not nom:
        return nom
    cle = re.sub(r"[^a-z0-9]", "", nom.lower())
    if cle in CORRECTIONS_PRONONCIATION_COMPAGNIE:
        return CORRECTIONS_PRONONCIATION_COMPAGNIE[cle]
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", nom)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return s


def contexte(plan, metar_o=None, metar_d=None):
    g, o, d, tm = plan["general"], plan["origin"], plan["destination"], plan["times"]
    vo, vd = nom_ville(o["icao_code"], o.get("name")), nom_ville(d["icao_code"], d.get("name"))
    mo, md = parse_metar(metar_o or o.get("metar")), parse_metar(metar_d or d.get("metar"))
    fn = vol_parle(g.get("flight_number", ""))
    du = duree_parlee(tm.get("est_time_enroute") or tm.get("sched_time_enroute") or 7200)
    to, td = temp_parlee(mo["temp"]), temp_parlee(md["temp"])
    so, sd = ciel_parle(mo), ciel_parle(md)
    wd = vent_parle(md)
    cm = commentaire(md)
    tu = turbulence_parle(plan)
    EW = {L: embellir_nom_compagnie(COMPAGNIE) for L in LANGS}
    nom = " %s" % NOM_EQUIPAGE if NOM_EQUIPAGE else ""  # ex: "chef de cabine Sophie" (sans parentheses, plus naturel a l'oral)

    # --- heure reelle courante (SimConnect ZULU TIME), repli SimBrief ---
    try:
        tz_o = float(str(o.get("timezone") or 0))
    except Exception:
        tz_o = 0.0
    heure_utc_reelle = None
    # 1) reutiliser en priorite la connexion SimConnect deja active et
    #    entretenue par surveillance_simconnect() (si la boucle tourne) :
    #    ouvrir ici une 2e connexion concurrente avec un timeout court
    #    (ancien code : 500 ms) echouait souvent silencieusement - la
    #    donnee ZULU_TIME n'avait pas le temps d'etre peuplee - et on
    #    retombait alors sur l'heure PREVUE du plan SimBrief au lieu de
    #    l'heure REELLE, d'ou des annonces "vol de nuit" declenchees a
    #    tort en plein apres-midi.
    if _AQ_SIMCONNECT_ACTIF is not None:
        try:
            zt = _AQ_SIMCONNECT_ACTIF.get("ZULU_TIME")
            if zt is not None:
                heure_utc_reelle = (float(zt) / 3600.0) % 24.0
                _journal("contexte(): ZULU_TIME via connexion active = %.3fh UTC" % heure_utc_reelle)
        except Exception as ex:
            _journal("contexte(): lecture ZULU_TIME via connexion active impossible : %r" % ex)
            heure_utc_reelle = None
    # 2) sinon (pas de boucle de surveillance en cours, ex. regeneration
    #    manuelle --vol/--tout), ouvrir une connexion dediee avec un
    #    timeout plus large (2000 ms, comme surveillance_simconnect) et
    #    quelques tentatives, le temps que SimConnect peuple la donnee.
    if heure_utc_reelle is None:
        try:
            from SimConnect import SimConnect, AircraftRequests
            _sm_h = SimConnect()
            _aq_h = AircraftRequests(_sm_h, _time=2000)
            for _tentative in range(3):
                zt = _aq_h.get("ZULU_TIME")
                if zt is not None:
                    heure_utc_reelle = (float(zt) / 3600.0) % 24.0
                    break
                time.sleep(0.3)
            _sm_h.exit()
            if heure_utc_reelle is not None:
                _journal("contexte(): ZULU_TIME via connexion dediee = %.3fh UTC" % heure_utc_reelle)
            else:
                _journal("contexte(): ZULU_TIME indisponible apres 3 tentatives, repli plan SimBrief.")
        except Exception as ex:
            _journal("contexte(): connexion SimConnect dediee impossible (%r), repli plan SimBrief." % ex)
            heure_utc_reelle = None
    if heure_utc_reelle is not None:
        minute_locale = int(round((heure_utc_reelle + tz_o) * 60.0)) % 1440
    else:
        try:
            base_t = int(tm.get("est_out") or tm.get("sched_out") or 0)
        except Exception:
            base_t = 0
        if base_t:
            _tl = time.gmtime(base_t + int(tz_o * 3600))
            minute_locale = _tl.tm_hour * 60 + _tl.tm_min
        else:
            minute_locale = 12 * 60
    heure_locale = minute_locale // 60

    # --- retard : compare l'heure PREVUE de depart a l'heure REELLE ---
    retard_min = 0
    try:
        sched_out = int(tm.get("sched_out") or 0)
        if sched_out:
            _tl_prevu = time.gmtime(sched_out + int(tz_o * 3600))
            minute_prevu = _tl_prevu.tm_hour * 60 + _tl_prevu.tm_min
            if heure_utc_reelle is not None:
                ecart = (minute_locale - minute_prevu) % 1440
                if ecart <= 720:
                    retard_min = ecart
            else:
                est_out = int(tm.get("est_out") or sched_out)
                retard_min = max(0, (est_out - sched_out) // 60)
    except Exception:
        retard_min = 0
    if retard_min >= 15:
        RETARD = {
            "fr": " Nous sommes désolés de vous informer que notre départ est retardé d'environ %d minutes ; nous ferons de notre mieux pour rattraper ce retard en vol. Merci de votre patience." % retard_min,
            "en": " We are sorry to inform you that our departure is delayed by about %d minutes; we will do our best to make up for the delay during the flight. Thank you for your patience." % retard_min,
            "de": " Wir bedauern, Ihnen mitteilen zu müssen, dass sich unser Abflug um etwa %d Minuten verzögert; wir werden unser Bestes tun, um die Verspätung während des Flugs aufzuholen. Vielen Dank für Ihre Geduld." % retard_min,
            "es": " Lamentamos informarles de que nuestra salida se retrasa unos %d minutos; haremos lo posible por recuperar el retraso durante el vuelo. Gracias por su paciencia." % retard_min,
        }
    else:
        RETARD = {L: "" for L in LANGS}

    # --- repas : menu + boissons selon l'heure locale REELLE a l'origine ---
    nuit_embarquement = (minute_locale >= 22 * 60 or minute_locale < 6 * 60)
    if nuit_embarquement:
        AMBIANCE_NUIT = {
            "fr": " Comme notre vol a lieu de nuit, nous avons baissé l'éclairage de la cabine pour votre confort ; des masques pour les yeux, des bouchons d'oreille et des couvertures sont à votre disposition sur simple demande auprès de notre équipage.",
            "en": " As this is a night flight, we have dimmed the cabin lighting for your comfort; eye masks, earplugs and blankets are available on request from our crew.",
            "de": " Da es sich um einen Nachtflug handelt, haben wir die Kabinenbeleuchtung zu Ihrem Komfort gedimmt; Augenmasken, Ohrstöpsel und Decken erhalten Sie auf Anfrage bei unserer Crew.",
            "es": " Al tratarse de un vuelo nocturno, hemos atenuado la iluminación de la cabina para su comodidad; antifaces, tapones para los oídos y mantas están disponibles bajo petición a nuestra tripulación.",
        }
    else:
        AMBIANCE_NUIT = {L: "" for L in LANGS}

    WIFI_DIVERTISSEMENT = {
        "fr": " Pour vous divertir pendant le vol, connectez-vous au réseau Wi-Fi à bord : films, séries et presse numérique sont accessibles gratuitement en streaming depuis votre propre téléphone ou tablette.",
        "en": " To keep you entertained during the flight, connect to our onboard Wi-Fi network: movies, TV shows and digital magazines are available free of charge, streamed to your own phone or tablet.",
        "de": " Zu Ihrer Unterhaltung während des Fluges verbinden Sie sich bitte mit unserem Bord-WLAN: Filme, Serien und digitale Zeitschriften stehen kostenlos zum Streamen auf Ihrem eigenen Smartphone oder Tablet bereit.",
        "es": " Para su entretenimiento durante el vuelo, conéctese a nuestra red Wi-Fi de a bordo: películas, series y prensa digital están disponibles gratis en streaming desde su propio teléfono o tableta.",
    }

    # --- service a bord specifique a la compagnie identifiee (cf. SERVICES_BORD) ---
    _cle_compagnie = re.sub(r"[^a-z0-9]", "", (COMPAGNIE or "").lower())
    _svc = SERVICES_BORD.get(_cle_compagnie)
    if _svc and _svc.get("wifi"):
        WIFI_DIVERTISSEMENT = _svc["wifi"]
    if _svc and _svc.get("annonces"):
        _choix_svc = random.choice(_svc["annonces"])
        SERVICE_COMPAGNIE = {L: " " + _choix_svc[L] for L in LANGS}
    else:
        SERVICE_COMPAGNIE = {L: "" for L in LANGS}

    MENUS = {
        "petit_dej": {
            "fr": ["un petit-déjeuner continental avec viennoiserie, fromage frais et fruits",
                   "un petit-déjeuner chaud avec omelette, pain grillé et confiture"],
            "en": ["a continental breakfast with pastry, fresh cheese and fruit",
                   "a hot breakfast with omelette, toast and jam"],
            "de": ["ein kontinentales Frühstück mit Gebäck, Frischkäse und Obst",
                   "ein warmes Frühstück mit Omelett, Toast und Marmelade"],
            "es": ["un desayuno continental con bollería, queso fresco y fruta",
                   "un desayuno caliente con tortilla, tostadas y mermelada"],
        },
        "dejeuner": {
            "fr": ["un plat de poulet rôti, riz et légumes de saison",
                   "un plat de pâtes aux légumes méditerranéens",
                   "un plat de saumon, purée et haricots verts"],
            "en": ["roast chicken with rice and seasonal vegetables",
                   "pasta with Mediterranean vegetables",
                   "salmon with mashed potatoes and green beans"],
            "de": ["gebratenes Hähnchen mit Reis und Gemüse der Saison",
                   "Nudeln mit mediterranem Gemüse",
                   "Lachs mit Kartoffelpüree und grünen Bohnen"],
            "es": ["pollo asado con arroz y verduras de temporada",
                   "pasta con verduras mediterráneas",
                   "salmón con puré de patata y judías verdes"],
        },
        "collation": {
            "fr": ["une collation sucrée-salée avec sandwich et pâtisserie",
                   "une collation avec salade composée et gâteau"],
            "en": ["a sweet and savoury snack with a sandwich and pastry",
                   "a snack with a mixed salad and cake"],
            "de": ["einen süß-herzhaften Snack mit Sandwich und Gebäck",
                   "einen Snack mit gemischtem Salat und Kuchen"],
            "es": ["un tentempié dulce y salado con sándwich y bollería",
                   "un tentempié con ensalada variada y pastel"],
        },
        "diner": {
            "fr": ["un dîner avec filet de poulet, pommes de terre et légumes",
                   "un dîner avec risotto aux champignons",
                   "un dîner avec poisson, riz et légumes verts"],
            "en": ["chicken fillet with potatoes and vegetables",
                   "mushroom risotto",
                   "fish with rice and green vegetables"],
            "de": ["Hähnchenfilet mit Kartoffeln und Gemüse",
                   "Pilzrisotto",
                   "Fisch mit Reis und grünem Gemüse"],
            "es": ["filete de pollo con patatas y verduras",
                   "risotto de setas",
                   "pescado con arroz y verduras verdes"],
        },
        # encas du matin (8h-11h) : cafe/the/boisson chaude + une petite douceur,
        # plus leger qu'une vraie collation.
        "encas_matin": {
            "fr": ["un café, un thé ou une boisson chaude, avec une viennoiserie",
                   "une boisson chaude accompagnée d'un biscuit"],
            "en": ["coffee, tea or a hot drink, with a pastry",
                   "a hot drink with a biscuit"],
            "de": ["Kaffee, Tee oder ein heißes Getränk, mit einem Gebäckstück",
                   "ein heißes Getränk mit einem Keks"],
            "es": ["café, té o una bebida caliente, con un dulce",
                   "una bebida caliente con una galleta"],
        },
        # encas de l'apres-midi (14h-16h) : pause plus "gourmande", sucree.
        "encas_apresmidi": {
            "fr": ["une collation gourmande avec pâtisserie ou chocolat",
                   "un encas sucré avec gâteau et boisson fraîche"],
            "en": ["a sweet treat with pastry or chocolate",
                   "a sweet snack with cake and a cold drink"],
            "de": ["einen süßen Snack mit Gebäck oder Schokolade",
                   "einen süßen Imbiss mit Kuchen und einem kalten Getränk"],
            "es": ["un tentempié goloso con bollería o chocolate",
                   "un snack dulce con pastel y una bebida fresca"],
        },
    }
    BOISSONS = {"fr": "eau, jus de fruits, sodas, thé, café, et une sélection de vins et bières",
                "en": "water, fruit juice, soft drinks, tea, coffee, and a selection of wines and beers",
                "de": "Wasser, Fruchtsaft, Softdrinks, Tee, Kaffee sowie eine Auswahl an Wein und Bier",
                "es": "agua, zumo de frutas, refrescos, té, café, y una selección de vinos y cervezas"}

    if nuit_embarquement:
        REPAS = {
            "fr": "Comme il s'agit d'un vol de nuit, le service sera léger : boissons et encas sont à votre disposition aux emplacements prévus dans la cabine ; n'hésitez pas à solliciter notre équipage.",
            "en": "As this is a night flight, service will be light: drinks and snacks are available at the locations provided in the cabin; please do not hesitate to ask our crew.",
            "de": "Da es sich um einen Nachtflug handelt, fällt der Service schlicht aus: Getränke und Snacks finden Sie an den dafür vorgesehenen Stellen in der Kabine ; sprechen Sie gerne unsere Crew an.",
            "es": "Al tratarse de un vuelo nocturno, el servicio será ligero: bebidas y tentempiés están disponibles en los lugares previstos de la cabina; no duden en pedírselo a la tripulación.",
        }
    else:
        # horaires precises par Herve (23/11/2026) : petit-dejeuner 6h-8h,
        # encas/boisson chaude 8h-11h, dejeuner 11h-13h, encas gourmand
        # 14h-16h, diner 19h-21h ; en dehors de ces creneaux (13h-14h,
        # 16h-19h, 21h-22h), collation generique par defaut.
        if 6 * 60 <= minute_locale < 8 * 60:
            cle, moment = "petit_dej", {"fr": "Comme il est tôt, nous vous proposons", "en": "As it is still early, we are offering you",
                                         "de": "Da es noch früh ist, bieten wir Ihnen", "es": "Como es temprano, les proponemos"}
        elif 8 * 60 <= minute_locale < 11 * 60:
            cle, moment = "encas_matin", {"fr": "En attendant, nous vous proposons", "en": "In the meantime, we are offering you",
                                           "de": "In der Zwischenzeit bieten wir Ihnen", "es": "Mientras tanto, les proponemos"}
        elif 11 * 60 <= minute_locale < 13 * 60:
            cle, moment = "dejeuner", {"fr": "Pour le déjeuner, nous vous proposons", "en": "For lunch, we are offering you",
                                        "de": "Zum Mittagessen bieten wir Ihnen", "es": "Para el almuerzo, les proponemos"}
        elif 14 * 60 <= minute_locale < 16 * 60:
            cle, moment = "encas_apresmidi", {"fr": "Pour une pause gourmande, nous vous proposons", "en": "For a sweet break, we are offering you",
                                               "de": "Für eine süße Pause bieten wir Ihnen", "es": "Para una pausa golosa, les proponemos"}
        elif 19 * 60 <= minute_locale < 21 * 60:
            cle, moment = "diner", {"fr": "Pour le dîner, nous vous proposons", "en": "For dinner, we are offering you",
                                     "de": "Zum Abendessen bieten wir Ihnen", "es": "Para la cena, les proponemos"}
        else:
            cle, moment = "collation", {"fr": "Nous vous proposons", "en": "We are offering you",
                                         "de": "Wir bieten Ihnen", "es": "Les proponemos"}
        REPAS = {}
        for L in LANGS:
            menu_choisi = random.choice(MENUS[cle][L])
            if L == "fr":
                # BOISSONS["fr"] commence par "eau" (voyelle) : elision "d'", pas "de"
                REPAS[L] = "%s %s, accompagné d'%s." % (moment[L], menu_choisi, BOISSONS[L])
            elif L == "en":
                REPAS[L] = "%s %s, with %s." % (moment[L], menu_choisi, BOISSONS[L])
            elif L == "de":
                REPAS[L] = "%s %s, dazu %s." % (moment[L], menu_choisi, BOISSONS[L])
            else:
                REPAS[L] = "%s %s, junto con %s." % (moment[L], menu_choisi, BOISSONS[L])

    # --- scenarios rares supprimes : on reste simple, pas de scenario special ---
    SCENARIO = {L: "" for L in LANGS}

    # --- salutation de fin de service, selon l'heure et le jour REELS (poste de l'equipage) ---
    SALUT = salut_fin_service_par_langue()

    out = {}
    for L in LANGS:
        out[L] = dict(EW=EW[L], FN=fn[L], ORIG=vo[L], DEST=vd[L], DUR=du[L], TEMP_O=to[L], TEMP_D=td[L],
                      SKY_O=so[L], SKY_D=sd[L], WIND_D=wd[L], COMMENT_D=cm[L], TURB=tu[L], NOM=nom,
                      RETARD=RETARD[L], REPAS=REPAS[L], SCENARIO=SCENARIO[L], SERVICE_COMPAGNIE=SERVICE_COMPAGNIE[L],
                      AMBIANCE_NUIT=AMBIANCE_NUIT[L], WIFI=WIFI_DIVERTISSEMENT[L], SALUT=SALUT[L])
    return out


# ------------------------------------------------------------------ textes : (type, avec_carillon, personnalisé, [(fr, en), ...])
T = []


def add(nom, carillon, perso, variantes):
    T.append((nom, carillon, perso, variantes))


add("BoardingWelcome", True, True, [
    {"fr": "Mesdames et messieurs, bienvenue à bord de ce vol {EW} {FN}, à destination de {DEST}. Ici votre chef de cabine{NOM}.{RETARD}{AMBIANCE_NUIT} Installez-vous, et rangez vos bagages à main dans les coffres au-dessus de vos sièges, ou sous le siège devant vous. Si votre compartiment est complet, un membre de l'équipage se tient à votre disposition. Merci de votre patience.{WIFI}",
     "en": "Ladies and gentlemen, welcome aboard {EW} flight {FN} to {DEST}. This is your cabin manager{NOM} speaking.{RETARD}{AMBIANCE_NUIT} Please make yourselves comfortable, and stow your hand luggage in the overhead lockers, or under the seat in front of you. If your locker is full, a crew member will be happy to assist you. Thank you for your patience.{WIFI}",
     "de": "Meine Damen und Herren, willkommen an Bord von {EW} Flug {FN} nach {DEST}. Hier spricht Ihr Kabinenchef{NOM}.{RETARD}{AMBIANCE_NUIT} Machen Sie es sich bequem und verstauen Sie Ihr Handgepäck in den Gepäckfächern über Ihrem Sitz oder unter dem Sitz vor Ihnen. Sollte Ihr Gepäckfach voll sein, hilft Ihnen gerne ein Mitglied der Kabinencrew weiter. Vielen Dank für Ihre Geduld.{WIFI}",
     "es": "Señoras y señores, bienvenidos a bordo del vuelo {EW} {FN} con destino a {DEST}. Les habla su jefe de cabina{NOM}.{RETARD}{AMBIANCE_NUIT} Pónganse cómodos y guarden su equipaje de mano en los compartimentos superiores, o bajo el asiento delantero. Si su compartimento está lleno, un miembro de la tripulación estará encantado de ayudarle. Gracias por su paciencia.{WIFI}"},
    {"fr": "Bienvenue à bord, mesdames et messieurs. Votre équipage vous souhaite un excellent vol {EW} à destination de {DEST}. Le temps de vol sera d'environ {DUR}. À {ORIG}, il fait actuellement {TEMP_O}, {SKY_O}. Prenez place, et rangez vos affaires. Merci.",
     "en": "Welcome aboard, ladies and gentlemen. Your crew wishes you an excellent {EW} flight to {DEST}. Our flight time will be about {DUR}. In {ORIG}, it is currently {TEMP_O}, {SKY_O}. Please take your seats, and stow your belongings. Thank you.",
     "de": "Willkommen an Bord, meine Damen und Herren. Ihre Crew wünscht Ihnen einen angenehmen {EW}-Flug nach {DEST}. Die Flugzeit beträgt etwa {DUR}. In {ORIG} ist es derzeit {TEMP_O}, {SKY_O}. Nehmen Sie Platz, und verstauen Sie Ihre Sachen. Vielen Dank.",
     "es": "Bienvenidos a bordo, señoras y señores. Su tripulación les desea un excelente vuelo {EW} con destino a {DEST}. El tiempo de vuelo será de aproximadamente {DUR}. En {ORIG} hace actualmente {TEMP_O}, {SKY_O}. Tomen asiento, y guarden sus pertenencias. Gracias."},
    {"fr": "Mesdames et messieurs, l'équipage de ce vol {EW} {FN} est heureux de vous accueillir à bord. Nous nous rendons à {DEST}. Pendant que vous vous installez, merci de ranger vos bagages, et de laisser les allées libres. Des membres de l'équipage sont à votre disposition pour vous aider à ranger vos bagages. Merci.",
     "en": "Ladies and gentlemen, the crew of {EW} flight {FN} is delighted to welcome you on board. We are heading to {DEST}. While you settle in, please stow your bags, and keep the aisle clear. Crew members are available to help you stow your luggage. Thank you.",
     "de": "Meine Damen und Herren, die Crew von {EW} Flug {FN} freut sich, Sie an Bord willkommen zu heißen. Unser Ziel ist {DEST}. Während Sie sich einrichten, verstauen Sie bitte Ihr Gepäck und halten Sie den Gang frei. Mitglieder der Kabinencrew helfen Ihnen gerne beim Verstauen Ihres Gepäcks. Vielen Dank.",
     "es": "Señoras y señores, la tripulación del vuelo {EW} {FN} se complace en darles la bienvenida a bordo. Nos dirigimos a {DEST}. Mientras se instalan, les rogamos guardar su equipaje y dejar el pasillo libre. Miembros de la tripulación están a su disposición para ayudarles a guardar su equipaje. Gracias."},
])
add("BoardingComplete", True, True, [
    {"fr": "Mesdames et messieurs, l'embarquement est à présent terminé, merci d'avoir été aussi ponctuels. Nous allons bientôt fermer les portes. Votre temps de vol jusqu'à {DEST} sera d'environ {DUR}. Merci de passer vos appareils électroniques en mode avion.",
     "en": "Ladies and gentlemen, boarding is now complete. Thank you for being so punctual. We will close the doors shortly. Your flight time to {DEST} will be about {DUR}. Please switch your electronic devices to flight mode.",
     "de": "Meine Damen und Herren, das Boarding ist abgeschlossen. Vielen Dank, dass Sie so pünktlich waren. Wir werden die Türen in Kürze schließen. Ihre Flugzeit nach {DEST} beträgt etwa {DUR}. Bitte schalten Sie Ihre elektronischen Geräte in den Flugmodus.",
     "es": "Señoras y señores, el embarque ha finalizado. Gracias por ser tan puntuales. En breve cerraremos las puertas. Su tiempo de vuelo hasta {DEST} será de aproximadamente {DUR}. Pongan sus dispositivos electrónicos en modo avión."},
    {"fr": "Mesdames et messieurs, tout le monde est à bord, c'est parfait. Les portes vont être fermées. Nous volerons vers {DEST} pendant environ {DUR}. Veuillez attacher votre ceinture, et mettre vos téléphones en mode avion. Merci.",
     "en": "Ladies and gentlemen, everybody is on board, which is perfect. The doors will now be closed. We will be flying to {DEST} for about {DUR}. Please fasten your seat belt, and put your phones in flight mode. Thank you.",
     "de": "Meine Damen und Herren, alle sind an Bord, perfekt. Die Türen werden nun geschlossen. Wir fliegen etwa {DUR} nach {DEST}. Bitte schließen Sie Ihren Sicherheitsgurt und schalten Sie Ihre Telefone in den Flugmodus. Vielen Dank.",
     "es": "Señoras y señores, todo el mundo está a bordo, perfecto. Las puertas van a cerrarse. Volaremos hacia {DEST} durante aproximadamente {DUR}. Abróchense el cinturón de seguridad y pongan sus teléfonos en modo avión. Gracias."},
    {"fr": "Mesdames et messieurs, l'embarquement est maintenant terminé, l'équipage vous remercie et vous souhaite un excellent vol {EW} jusqu'à {DEST}. Merci de rester assis, de relever votre tablette, et de porter toute votre attention à la démonstration de sécurité.",
     "en": "Ladies and gentlemen, boarding is now complete. The crew thanks you, and wishes you an excellent {EW} flight to {DEST}. Please remain seated, stow your tray table, and give your full attention to the safety demonstration.",
     "de": "Meine Damen und Herren, das Boarding ist nun abgeschlossen. Die Crew bedankt sich und wünscht Ihnen einen ausgezeichneten {EW}-Flug nach {DEST}. Bitte bleiben Sie sitzen, klappen Sie Ihren Tisch hoch, und schenken Sie der Sicherheitsvorführung Ihre volle Aufmerksamkeit.",
     "es": "Señoras y señores, el embarque ha finalizado. La tripulación les agradece y les desea un excelente vuelo {EW} hasta {DEST}. Permanezcan sentados, suban su mesita, y presten toda su atención a la demostración de seguridad."},
])
add("ArmDoors", False, False, [
    {"fr": "Personnel de cabine, armez les portes et vérifiez en croisé.", "en": "Cabin crew, arm doors and cross-check.",
     "de": "Kabinenpersonal, Türen scharf schalten und Kreuzkontrolle durchführen.", "es": "Personal de cabina, armen las puertas y verifiquen en cruzado."},
    {"fr": "Équipage, portes en automatique, et contrôle croisé.", "en": "Crew, doors to automatic, and cross-check.",
     "de": "Crew, Türen auf automatisch, und Kreuzkontrolle.", "es": "Tripulación, puertas en automático, y control cruzado."},
])
add("DisarmDoors", False, False, [
    {"fr": "Personnel de cabine, désarmez les portes et vérifiez en croisé.", "en": "Cabin crew, disarm doors and cross-check.",
     "de": "Kabinenpersonal, Türen entschärfen und Kreuzkontrolle durchführen.", "es": "Personal de cabina, desarmen las puertas y verifiquen en cruzado."},
    {"fr": "Équipage, portes en manuel, et contrôle croisé.", "en": "Crew, doors to manual, and cross-check.",
     "de": "Crew, Türen auf manuell, und Kreuzkontrolle.", "es": "Tripulación, puertas en manual, y control cruzado."},
])
add("PreSafetyBriefing", True, False, [
    {"fr": "Mesdames et messieurs, votre attention s'il vous plaît. Nous allons commencer la démonstration de sécurité.",
     "en": "Ladies and gentlemen, may we have your attention please. We are about to begin the safety demonstration.",
     "de": "Meine Damen und Herren, wir bitten um Ihre Aufmerksamkeit. Wir beginnen nun mit der Sicherheitsvorführung.",
     "es": "Señoras y señores, su atención por favor. Vamos a comenzar la demostración de seguridad."},
    {"fr": "Mesdames et messieurs, quelques instants d'attention pour les consignes de sécurité, merci.",
     "en": "Ladies and gentlemen, a few moments of your attention for the safety instructions, please.",
     "de": "Meine Damen und Herren, wir bitten Sie kurz um Ihre Aufmerksamkeit für die Sicherheitshinweise, danke.",
     "es": "Señoras y señores, unos instantes de atención para las instrucciones de seguridad, gracias."},
    {"fr": "Mesdames et messieurs, si vous voulez bien lever les yeux de votre téléphone, la démonstration de sécurité va commencer.",
     "en": "Ladies and gentlemen, if you could look up from your phone for a moment, the safety demonstration is about to begin.",
     "de": "Meine Damen und Herren, wenn Sie bitte kurz von Ihrem Telefon aufschauen könnten, die Sicherheitsvorführung beginnt gleich.",
     "es": "Señoras y señores, si pudieran levantar la vista de su teléfono un momento, la demostración de seguridad va a comenzar."},
])
add("SafetyBriefing", False, False, [
    {"fr": "Il y a quatre sorties de secours, deux à l'avant, deux à l'arrière. Elles sont signalées par des bandes lumineuses au sol. La ceinture : on l'attache en insérant la languette dans la boucle, et on la détache en ouvrant la boucle. En cas de dépressurisation, des masques tomberont automatiquement. Tirez sur un masque, placez-le sur le nez et la bouche, et respirez normalement. Si vous voyagez avec des enfants, mettez d'abord votre propre masque, puis aidez les enfants qui vous accompagnent. Votre gilet de sauvetage est sous votre siège. Ne le gonflez qu'à l'extérieur de l'appareil. Enfin, il est interdit de fumer à bord, y compris dans les toilettes. Merci de votre attention, et bon vol avec {EW}.",
     "en": "There are four emergency exits, two at the front, two at the back. They are marked by lights along the floor. Seat belts: insert the tab into the buckle to fasten, and open the buckle to release. In case of depressurisation, oxygen masks will drop automatically. Pull a mask towards you, place it over your nose and mouth, and breathe normally. If you are travelling with children, put your own mask on first, then assist the children travelling with you. Your life jacket is under your seat. Inflate it only once you are outside the aircraft. Finally, smoking is prohibited on board, including in the lavatories. Thank you for your attention, and enjoy your flight with {EW}.",
     "de": "Es gibt vier Notausgänge, zwei vorne und zwei hinten. Sie sind durch Lichtleisten am Boden markiert. Der Sicherheitsgurt: Sie schließen ihn, indem Sie die Zunge in die Schnalle stecken, und öffnen ihn, indem Sie die Schnalle öffnen. Bei Druckverlust fallen automatisch Sauerstoffmasken herab. Ziehen Sie an einer Maske, setzen Sie sie auf Nase und Mund, und atmen Sie normal. Wenn Sie mit Kindern reisen, setzen Sie zuerst Ihre eigene Maske auf und helfen Sie anschließend den Kindern. Ihre Schwimmweste befindet sich unter Ihrem Sitz. Blasen Sie sie erst außerhalb des Flugzeugs auf. Schließlich ist das Rauchen an Bord verboten, auch in den Toiletten. Vielen Dank für Ihre Aufmerksamkeit, und einen guten Flug mit {EW}.",
     "es": "Hay cuatro salidas de emergencia, dos en la parte delantera y dos en la trasera. Están señaladas por bandas luminosas en el suelo. El cinturón: se abrocha insertando la lengüeta en la hebilla, y se desabrocha abriendo la hebilla. En caso de despresurización, las máscaras de oxígeno caerán automáticamente. Tire de una máscara, colóquela sobre la nariz y la boca, y respire con normalidad. Si viaja con niños, póngase primero su propia máscara y después ayude a los niños que le acompañan. Su chaleco salvavidas está bajo su asiento. Ínflelo solo fuera de la aeronave. Por último, está prohibido fumar a bordo, incluso en los baños. Gracias por su atención, y buen vuelo con {EW}."},
    {"fr": "Cette démonstration dure deux minutes et mérite toute votre attention. Les sorties de secours : repérez la plus proche, et comptez les rangées qui vous séparent d'elle. Elles sont signalées par des bandes lumineuses au sol. Le gilet de sauvetage se trouve sous votre siège. Ne le gonflez qu'une fois dehors. En cas de dépressurisation, les masques à oxygène tombent du plafond. Même si le sac ne se gonfle pas, l'oxygène circule, c'est normal. Si vous accompagnez un enfant, ou une personne qui a besoin d'aide, équipez-vous d'abord vous-même. Les appareils électroniques doivent rester en mode avion. Il est interdit de fumer, cigarettes électroniques comprises. Merci, et excellent vol à bord de {EW}.",
     "en": "This demonstration takes two minutes and deserves your full attention. Emergency exits: locate the nearest one, and count the rows between you and it. They are marked by lights along the floor. Your life jacket is under your seat. Inflate it only once you are outside. In case of depressurisation, oxygen masks will drop from the ceiling. Even if the bag does not inflate, oxygen is flowing, that is normal. If you are travelling with a child, or someone who needs assistance, fit your own mask first. Electronic devices must stay in flight mode. Smoking is prohibited, including electronic cigarettes. Thank you, and enjoy your flight on board {EW}.",
     "de": "Diese Vorführung dauert zwei Minuten und verdient Ihre volle Aufmerksamkeit. Die Notausgänge: Suchen Sie den nächstgelegenen, und zählen Sie die Reihen bis dorthin. Sie sind durch Lichtleisten am Boden markiert. Die Schwimmweste befindet sich unter Ihrem Sitz. Blasen Sie sie erst auf, wenn Sie draußen sind. Bei Druckverlust fallen die Sauerstoffmasken von der Decke. Auch wenn sich der Beutel nicht füllt, fließt Sauerstoff, das ist normal. Wenn Sie ein Kind begleiten, oder eine Person, die Hilfe benötigt, setzen Sie zuerst Ihre eigene Maske auf. Elektronische Geräte müssen im Flugmodus bleiben. Rauchen ist verboten, auch elektronische Zigaretten. Vielen Dank, und einen ausgezeichneten Flug mit {EW}.",
     "es": "Esta demostración dura dos minutos y merece toda su atención. Las salidas de emergencia: localice la más cercana, y cuente las filas que lo separan de ella. Están señaladas por bandas luminosas en el suelo. El chaleco salvavidas está bajo su asiento. Ínflelo solo una vez fuera. En caso de despresurización, las máscaras de oxígeno caen del techo. Aunque la bolsa no se infle, el oxígeno circula, es normal. Si acompaña a un niño, o a una persona que necesite ayuda, colóquese primero su propia máscara. Los dispositivos electrónicos deben permanecer en modo avión. Está prohibido fumar, incluidos los cigarrillos electrónicos. Gracias, y excelente vuelo a bordo de {EW}."},
    {"fr": "Pour votre sécurité, voici quelques informations à retenir. La sortie la plus proche peut se trouver derrière vous : repérez-la dès maintenant. Les sorties sont indiquées par des lumières vertes. Pour attacher votre ceinture, insérez la languette dans la boucle. Pour la détacher, ouvrez la boucle. En cas de dépressurisation, un masque tombera devant vous. Tirez dessus, placez-le sur le visage, et respirez normalement. Les gilets de sauvetage sont sous les sièges. Ne les gonflez qu'à l'extérieur de l'avion. Il est strictement interdit de fumer. Si vous avez des questions, notre équipage se fera un plaisir d'y répondre. Merci, et bon vol avec {EW}.",
     "en": "For your safety, here is some information worth remembering. The nearest exit may be behind you, so please locate it now. Exits are marked by green lights. To fasten your seat belt, insert the tab into the buckle. To release it, open the buckle. In case of depressurisation, a mask will drop in front of you. Pull it towards you, place it over your face, and breathe normally. Life jackets are under the seats. Inflate them only outside the aircraft. Smoking is strictly prohibited. If you have any questions, our crew will be happy to answer them. Thank you, and enjoy your flight with {EW}.",
     "de": "Für Ihre Sicherheit hier einige wichtige Informationen. Der nächste Ausgang könnte hinter Ihnen sein, suchen Sie ihn bitte jetzt. Die Ausgänge sind durch grüne Lichter markiert. Um Ihren Gurt zu schließen, stecken Sie die Zunge in die Schnalle. Um ihn zu öffnen, öffnen Sie die Schnalle. Bei Druckverlust fällt eine Maske vor Ihnen herab. Ziehen Sie daran, setzen Sie sie auf Ihr Gesicht, und atmen Sie normal. Die Schwimmwesten befinden sich unter den Sitzen. Blasen Sie sie erst außerhalb des Flugzeugs auf. Rauchen ist strikt verboten. Falls Sie Fragen haben, beantwortet unsere Crew diese gerne. Vielen Dank, und einen guten Flug mit {EW}.",
     "es": "Por su seguridad, aquí tienen algo de información que recordar. La salida más cercana puede estar detrás de ustedes, localícenla ahora. Las salidas están señaladas con luces verdes. Para abrocharse el cinturón, inserte la lengüeta en la hebilla. Para desabrocharlo, abra la hebilla. En caso de despresurización, una máscara caerá frente a usted. Tire de ella, colóquela sobre el rostro, y respire con normalidad. Los chalecos salvavidas están bajo los asientos. Ínflelos solo fuera del avión. Está estrictamente prohibido fumar. Si tienen alguna pregunta, nuestra tripulación responderá con gusto. Gracias, y buen vuelo con {EW}."},
])
add("CrewTakeSeats", False, False, [
    {"fr": "Personnel de cabine, prenez place.", "en": "Cabin crew, take your seats.",
     "de": "Kabinenpersonal, bitte Plätze einnehmen.", "es": "Personal de cabina, tomen asiento."},
    {"fr": "Équipage, asseyez-vous, s'il vous plaît.", "en": "Crew, please be seated.",
     "de": "Crew, bitte setzen.", "es": "Tripulación, siéntense, por favor."},
])
add("CabinDim", False, False, [
    {"fr": "Mesdames et messieurs, nous allons baisser l'éclairage de la cabine. Merci de relever les stores si vous êtes près d'un hublot.",
     "en": "Ladies and gentlemen, we will now dim the cabin lights. Please raise your window shades if you are seated by a window.",
     "de": "Meine Damen und Herren, wir werden nun die Kabinenbeleuchtung dimmen. Bitte öffnen Sie die Fensterblenden, falls Sie am Fenster sitzen.",
     "es": "Señoras y señores, vamos a reducir la iluminación de la cabina. Suban las persianas si están cerca de una ventanilla."},
    {"fr": "Mesdames et messieurs, la cabine va être plongée dans la pénombre. Merci de relever les stores si vous êtes près d'un hublot.",
     "en": "Ladies and gentlemen, the cabin lights will now be dimmed. Please raise your window shades if you are seated by a window.",
     "de": "Meine Damen und Herren, die Kabine wird nun abgedunkelt. Bitte öffnen Sie die Fensterblenden, falls Sie am Fenster sitzen.",
     "es": "Señoras y señores, la cabina quedará en penumbra. Suban las persianas si están cerca de una ventanilla."},
])
add("CabinSecured", False, False, [
    {"fr": "Cabine sécurisée.", "en": "Cabin secured.", "de": "Kabine gesichert.", "es": "Cabina asegurada."},
    {"fr": "Cockpit, ici la cabine. La cabine est prête.", "en": "Flight deck, cabin crew. The cabin is ready.",
     "de": "Cockpit, hier die Kabine. Die Kabine ist bereit.", "es": "Cabina de mando, aquí cabina. La cabina está lista."},
])
add("AfterTakeoff", True, True, [
    {"fr": "Mesdames et messieurs, nous venons de décoller de {ORIG}. Ici le chef de cabine{NOM}. Notre temps de vol jusqu'à {DEST} sera d'environ {DUR}. À {ORIG}, il fait {TEMP_O}, {SKY_O}. À {DEST}, il fait {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} Nous reviendrons vers vous pour le service à bord. Merci.",
     "en": "Ladies and gentlemen, we have just taken off from {ORIG}. This is your cabin manager{NOM} speaking. Our flight time to {DEST} will be about {DUR}. In {ORIG}, it is {TEMP_O}, {SKY_O}. In {DEST}, it is {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} We will be back shortly with the service. Thank you.",
     "de": "Meine Damen und Herren, wir sind soeben von {ORIG} gestartet. Hier spricht Ihr Kabinenchef{NOM}. Unsere Flugzeit nach {DEST} beträgt etwa {DUR}. In {ORIG} ist es {TEMP_O}, {SKY_O}. In {DEST} ist es {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} Wir kommen in Kürze mit dem Service zu Ihnen zurück. Vielen Dank.",
     "es": "Señoras y señores, acabamos de despegar de {ORIG}. Les habla el jefe de cabina{NOM}. Nuestro tiempo de vuelo hasta {DEST} será de aproximadamente {DUR}. En {ORIG} hace {TEMP_O}, {SKY_O}. En {DEST} hace {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} Volveremos pronto con el servicio a bordo. Gracias."},
    {"fr": "Mesdames et messieurs, le commandant et tout l'équipage vous souhaitent un agréable vol sur ce {EW} {FN}. Nous serons à {DEST} dans environ {DUR}. Là-bas, la température est de {TEMP_D}{WIND_D}. {COMMENT_D} {TURB} Vous pouvez dès maintenant ranger les manteaux, ou les ressortir, selon la destination. Merci.",
     "en": "Ladies and gentlemen, the captain and the whole crew wish you a pleasant flight on this {EW} {FN}. We will be in {DEST} in about {DUR}. There, the temperature is {TEMP_D}{WIND_D}. {COMMENT_D} {TURB} You may put your coats away now, or take them out again, depending on the destination. Thank you.",
     "de": "Meine Damen und Herren, der Kapitän und die gesamte Crew wünschen Ihnen einen angenehmen Flug mit diesem {EW} {FN}. Wir werden in etwa {DUR} in {DEST} sein. Dort beträgt die Temperatur {TEMP_D}{WIND_D}. {COMMENT_D} {TURB} Sie können Ihre Mäntel jetzt wegräumen, oder wieder herausholen, je nach Reiseziel. Vielen Dank.",
     "es": "Señoras y señores, el comandante y toda la tripulación les desean un agradable vuelo en este {EW} {FN}. Estaremos en {DEST} en aproximadamente {DUR}. Allí, la temperatura es de {TEMP_D}{WIND_D}. {COMMENT_D} {TURB} Ya pueden guardar los abrigos, o volver a sacarlos, según el destino. Gracias."},
    {"fr": "Mesdames et messieurs, nous sommes en route pour {DEST}. Le vol durera environ {DUR}. Au départ de {ORIG}, nous avions {TEMP_O}. À l'arrivée, ce sera plutôt {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} Installez-vous confortablement, nous passerons bientôt dans les allées. Merci.",
     "en": "Ladies and gentlemen, we are on our way to {DEST}. The flight will last about {DUR}. When we left {ORIG}, it was {TEMP_O}. On arrival, it will be more like {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} Please make yourselves comfortable, we will be coming through the aisles shortly. Thank you.",
     "de": "Meine Damen und Herren, wir befinden uns auf dem Weg nach {DEST}. Der Flug wird etwa {DUR} dauern. Beim Abflug von {ORIG} hatten wir {TEMP_O}. Bei der Ankunft wird es eher {TEMP_D}, {SKY_D} sein. {COMMENT_D} {TURB} Machen Sie es sich bequem, wir kommen bald durch die Gänge. Vielen Dank.",
     "es": "Señoras y señores, estamos en ruta hacia {DEST}. El vuelo durará aproximadamente {DUR}. Al salir de {ORIG}, teníamos {TEMP_O}. A la llegada, será más bien {TEMP_D}, {SKY_D}. {COMMENT_D} {TURB} Pónganse cómodos, pronto pasaremos por los pasillos. Gracias."},
])
add("SeatbeltSignOn", True, False, [
    {"fr": "Mesdames et messieurs, le signal ceinture vient d'être allumé. Merci de regagner votre place et d'attacher votre ceinture.",
     "en": "Ladies and gentlemen, the seat belt sign has been switched on. Please return to your seat and fasten your seat belt.",
     "de": "Meine Damen und Herren, das Anschnallzeichen wurde soeben eingeschaltet. Bitte kehren Sie zu Ihrem Platz zurück und schließen Sie Ihren Sicherheitsgurt.",
     "es": "Señoras y señores, se ha encendido la señal de abrocharse el cinturón. Regresen a su asiento y abróchense el cinturón."},
    {"fr": "Mesdames et messieurs, nous traversons une zone de turbulences. Veuillez regagner votre place et attacher votre ceinture.",
     "en": "Ladies and gentlemen, we are passing through an area of turbulence. Please return to your seat and fasten your seat belt.",
     "de": "Meine Damen und Herren, wir fliegen durch eine Turbulenzzone. Bitte kehren Sie zu Ihrem Platz zurück und schließen Sie Ihren Sicherheitsgurt.",
     "es": "Señoras y señores, estamos atravesando una zona de turbulencias. Regresen a su asiento y abróchense el cinturón."},
    {"fr": "Mesdames et messieurs, le commandant a allumé le signal ceinture. Merci de rester assis, ceinture attachée.",
     "en": "Ladies and gentlemen, the captain has switched on the seat belt sign. Please remain seated with your seat belt fastened.",
     "de": "Meine Damen und Herren, der Kapitän hat das Anschnallzeichen eingeschaltet. Bitte bleiben Sie sitzen, mit angelegtem Sicherheitsgurt.",
     "es": "Señoras y señores, el comandante ha encendido la señal de cinturón. Permanezcan sentados, con el cinturón abrochado."},
])
add("SeatbeltSignOff", True, False, [
    {"fr": "Mesdames et messieurs, le signal ceinture est éteint. Vous pouvez circuler dans la cabine. Nous vous recommandons toutefois de garder votre ceinture attachée lorsque vous êtes assis.",
     "en": "Ladies and gentlemen, the seat belt sign has been switched off. You may now move around the cabin. However, we recommend that you keep your seat belt fastened while seated.",
     "de": "Meine Damen und Herren, das Anschnallzeichen ist nun aus. Sie können sich in der Kabine bewegen. Wir empfehlen jedoch, den Sicherheitsgurt angelegt zu lassen, solange Sie sitzen.",
     "es": "Señoras y señores, la señal de cinturón se ha apagado. Pueden moverse por la cabina. Sin embargo, les recomendamos mantener el cinturón abrochado mientras estén sentados."},
    {"fr": "Mesdames et messieurs, le signal ceinture vient de s'éteindre. Vous êtes libres de vous déplacer. Les toilettes sont à l'avant et à l'arrière de l'appareil.",
     "en": "Ladies and gentlemen, the seat belt sign is now off. You are free to move around. The lavatories are at the front and the rear of the aircraft.",
     "de": "Meine Damen und Herren, das Anschnallzeichen ist soeben ausgegangen. Sie können sich frei bewegen. Die Toiletten befinden sich vorne und hinten im Flugzeug.",
     "es": "Señoras y señores, la señal de cinturón se acaba de apagar. Son libres de desplazarse. Los baños están en la parte delantera y trasera de la aeronave."},
])
add("CabinService", True, False, [
    {"fr": "Mesdames et messieurs, le service à bord va commencer. {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, the cabin service will begin shortly. {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, der Bordservice beginnt in Kürze. {REPAS}{SCENARIO}",
     "es": "Señoras y señores, el servicio a bordo va a comenzar. {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, notre équipage va maintenant commencer le service à bord. Merci de relever votre tablette. {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, our crew will now begin the cabin service. Please lower your tray table. {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, unsere Crew beginnt nun mit dem Bordservice. Bitte klappen Sie Ihren Tisch hoch. {REPAS}{SCENARIO}",
     "es": "Señoras y señores, nuestra tripulación va a comenzar ahora el servicio a bordo. Suban su mesita. {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, notre équipage va maintenant commencer le service à bord.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, our crew will now begin the cabin service.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, unsere Crew beginnt nun mit dem Bordservice.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "es": "Señoras y señores, nuestra tripulación va a comenzar ahora el servicio a bordo.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, le service à bord va commencer.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, the cabin service is about to begin.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, der Bordservice beginnt in Kürze.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "es": "Señoras y señores, el servicio a bordo va a comenzar.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, notre équipage passe maintenant dans les allées pour le service à bord.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, our crew is now coming through the aisles for the cabin service.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, unsere Crew kommt nun für den Bordservice durch die Gänge.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "es": "Señoras y señores, nuestra tripulación recorre ahora los pasillos para el servicio a bordo.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, le service à bord va commencer.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, the cabin service is about to begin.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, der Bordservice beginnt in Kürze.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "es": "Señoras y señores, el servicio a bordo va a comenzar.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, pendant que notre équipage prépare le service à bord,{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, while our crew prepares the cabin service,{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, während unsere Crew den Bordservice vorbereitet,{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "es": "Señoras y señores, mientras nuestra tripulación prepara el servicio a bordo,{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}"},
    {"fr": "Mesdames et messieurs, le service à bord va commencer.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "en": "Ladies and gentlemen, the cabin service is about to begin.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "de": "Meine Damen und Herren, der Bordservice beginnt in Kürze.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}",
     "es": "Señoras y señores, el servicio a bordo va a comenzar.{SERVICE_COMPAGNIE} {REPAS}{SCENARIO}"},
])
add("DescentStarted", True, True, [
    {"fr": "Mesdames et messieurs, nous avons commencé notre descente vers {DEST}. À {DEST}, il fait {TEMP_D}, {SKY_D}. {COMMENT_D} Veuillez regagner votre siège, attacher votre ceinture, relever votre tablette et remettre votre dossier en position verticale. Merci.",
     "en": "Ladies and gentlemen, we have started our descent into {DEST}. In {DEST}, it is {TEMP_D}, {SKY_D}. {COMMENT_D} Please return to your seat, fasten your seat belt, stow your tray table, and return your seat back to the upright position. Thank you.",
     "de": "Meine Damen und Herren, wir haben unseren Sinkflug nach {DEST} begonnen. In {DEST} ist es {TEMP_D}, {SKY_D}. {COMMENT_D} Bitte kehren Sie zu Ihrem Sitz zurück, schließen Sie Ihren Sicherheitsgurt, klappen Sie Ihren Tisch hoch und stellen Sie Ihre Rückenlehne aufrecht. Vielen Dank.",
     "es": "Señoras y señores, hemos iniciado nuestro descenso hacia {DEST}. En {DEST} hace {TEMP_D}, {SKY_D}. {COMMENT_D} Regresen a su asiento, abróchense el cinturón, suban su mesita y coloquen el respaldo en posición vertical. Gracias."},
    {"fr": "Mesdames et messieurs, nous allons bientôt atterrir à {DEST}. Température au sol : {TEMP_D}{WIND_D}. Merci de regagner votre place, de relever votre tablette, et de ranger tout ce qui traîne.",
     "en": "Ladies and gentlemen, we will shortly be landing in {DEST}. The temperature on the ground is {TEMP_D}{WIND_D}. Please return to your seat, stow your tray table, and put away anything lying around.",
     "de": "Meine Damen und Herren, wir werden in Kürze in {DEST} landen. Bodentemperatur: {TEMP_D}{WIND_D}. Bitte kehren Sie zu Ihrem Platz zurück, klappen Sie Ihren Tisch hoch, und verstauen Sie alles, was herumliegt.",
     "es": "Señoras y señores, en breve aterrizaremos en {DEST}. Temperatura en tierra: {TEMP_D}{WIND_D}. Regresen a su asiento, suban su mesita, y guarden todo lo que tengan suelto."},
    {"fr": "Mesdames et messieurs, nous entamons notre descente vers {DEST}. Il fait {TEMP_D} là-bas, {SKY_D}. Veuillez attacher votre ceinture, relever votre dossier, et vérifier que votre tablette est bien rangée. Merci de votre coopération.",
     "en": "Ladies and gentlemen, we are beginning our descent into {DEST}. It is {TEMP_D} down there, {SKY_D}. Please fasten your seat belt, return your seat back to the upright position, and check that your tray table is stowed. Thank you for your cooperation.",
     "de": "Meine Damen und Herren, wir beginnen unseren Sinkflug nach {DEST}. Dort ist es {TEMP_D}, {SKY_D}. Bitte schließen Sie Ihren Sicherheitsgurt, stellen Sie Ihre Rückenlehne aufrecht, und überprüfen Sie, dass Ihr Tisch hochgeklappt ist. Vielen Dank für Ihre Mitarbeit.",
     "es": "Señoras y señores, comenzamos nuestro descenso hacia {DEST}. Allí hace {TEMP_D}, {SKY_D}. Abróchense el cinturón, coloquen el respaldo en posición vertical, y comprueben que su mesita está plegada. Gracias por su cooperación."},
])
add("AfterLanding", True, True, [
    {"fr": "Mesdames et messieurs, bienvenue à {DEST}, où la température est de {TEMP_D}. Pour votre sécurité, restez assis, ceinture attachée, jusqu'à l'arrêt complet de l'appareil et l'extinction du signal. Nous vous remercions d'avoir choisi {EW}.",
     "en": "Ladies and gentlemen, welcome to {DEST}, where the temperature is {TEMP_D}. For your safety, please remain seated with your seat belt fastened until the aircraft has come to a complete stop and the sign has been switched off. Thank you for choosing {EW}.",
     "de": "Meine Damen und Herren, willkommen in {DEST}, wo die Temperatur {TEMP_D} beträgt. Zu Ihrer Sicherheit bleiben Sie bitte sitzen, mit angelegtem Sicherheitsgurt, bis das Flugzeug vollständig zum Stillstand gekommen ist und das Zeichen erlischt. Wir danken Ihnen, dass Sie sich für {EW} entschieden haben.",
     "es": "Señoras y señores, bienvenidos a {DEST}, donde la temperatura es de {TEMP_D}. Por su seguridad, permanezcan sentados, con el cinturón abrochado, hasta la parada completa de la aeronave y el apagado de la señal. Les agradecemos haber elegido {EW}."},
    {"fr": "Mesdames et messieurs, nous venons d'atterrir à {DEST}. {COMMENT_D} Restez assis jusqu'à l'extinction du signal ceinture. Merci.",
     "en": "Ladies and gentlemen, we have just landed in {DEST}. {COMMENT_D} Please remain seated until the seat belt sign has been switched off. Thank you.",
     "de": "Meine Damen und Herren, wir sind soeben in {DEST} gelandet. {COMMENT_D} Bleiben Sie sitzen, bis das Anschnallzeichen erlischt. Vielen Dank.",
     "es": "Señoras y señores, acabamos de aterrizar en {DEST}. {COMMENT_D} Permanezcan sentados hasta que se apague la señal de cinturón. Gracias."},
    {"fr": "Mesdames et messieurs, bienvenue à {DEST}. Il y fait {TEMP_D}, {SKY_D}. Merci de rester assis, ceinture attachée, jusqu'à l'arrêt complet de l'appareil.",
     "en": "Ladies and gentlemen, welcome to {DEST}. It is {TEMP_D} there, {SKY_D}. Please remain seated with your seat belt fastened until the aircraft has come to a complete stop.",
     "de": "Meine Damen und Herren, willkommen in {DEST}. Dort ist es {TEMP_D}, {SKY_D}. Bitte bleiben Sie sitzen, mit angelegtem Sicherheitsgurt, bis das Flugzeug vollständig zum Stillstand gekommen ist.",
     "es": "Señoras y señores, bienvenidos a {DEST}. Allí hace {TEMP_D}, {SKY_D}. Permanezcan sentados, con el cinturón abrochado, hasta la parada completa de la aeronave."},
])
add("DeboardingStarted", True, True, [
    {"fr": "Mesdames et messieurs, le débarquement commence. N'oubliez pas vos affaires personnelles. Merci d'avoir volé avec {EW}, nous espérons vous revoir très bientôt.",
     "en": "Ladies and gentlemen, deboarding is now starting. Please do not forget your personal belongings. Thank you for flying with {EW}, we hope to see you again very soon.",
     "de": "Meine Damen und Herren, das Aussteigen beginnt. Vergessen Sie bitte nicht Ihre persönlichen Gegenstände. Vielen Dank, dass Sie mit {EW} geflogen sind, wir hoffen, Sie bald wiederzusehen.",
     "es": "Señoras y señores, comienza el desembarque. No olviden sus pertenencias personales. Gracias por volar con {EW}, esperamos verles de nuevo muy pronto."},
    {"fr": "Mesdames et messieurs, vous pouvez maintenant quitter l'appareil. Merci de vérifier que vous n'avez rien oublié à bord. L'équipage de ce vol {FN} vous remercie, et vous souhaite un excellent séjour à {DEST}.",
     "en": "Ladies and gentlemen, you may now leave the aircraft. Please make sure you have not left anything on board. The crew of flight {FN} thanks you, and wishes you an excellent stay in {DEST}.",
     "de": "Meine Damen und Herren, Sie können das Flugzeug nun verlassen. Bitte überprüfen Sie, dass Sie nichts an Bord vergessen haben. Die Crew von Flug {FN} bedankt sich und wünscht Ihnen einen ausgezeichneten Aufenthalt in {DEST}.",
     "es": "Señoras y señores, ya pueden abandonar la aeronave. Comprueben que no han olvidado nada a bordo. La tripulación del vuelo {FN} les agradece y les desea una excelente estancia en {DEST}."},
    {"fr": "Mesdames et messieurs, le débarquement est ouvert. Nous vous remercions de votre confiance, et espérons que le vol vous a plu. Bon séjour à {DEST}, et à bientôt sur {EW}.",
     "en": "Ladies and gentlemen, deboarding has begun. Thank you for your trust, and we hope you enjoyed the flight. Enjoy your stay in {DEST}, and see you soon on {EW}.",
     "de": "Meine Damen und Herren, das Aussteigen ist freigegeben. Wir danken Ihnen für Ihr Vertrauen und hoffen, dass Ihnen der Flug gefallen hat. Einen schönen Aufenthalt in {DEST}, und bis bald bei {EW}.",
     "es": "Señoras y señores, el desembarque está abierto. Les agradecemos su confianza, y esperamos que hayan disfrutado del vuelo. Buena estancia en {DEST}, y hasta pronto en {EW}."},
])
add("DeboardingComplete", False, False, [
    {"fr": "Équipage, débarquement terminé. Merci pour votre travail. Nous vérifions la cabine et préparons le prochain vol.",
     "en": "Crew, deboarding is complete. Thank you for your work. We will check the cabin and prepare for the next flight.",
     "de": "Crew, Ausstieg abgeschlossen. Danke für eure Arbeit. Wir überprüfen die Kabine und bereiten den nächsten Flug vor.",
     "es": "Tripulación, desembarque finalizado. Gracias por su trabajo. Revisamos la cabina y preparamos el próximo vuelo."},
    {"fr": "Mesdames et messieurs de l'équipage, tous les passagers ont quitté l'appareil. Merci pour ce vol, et {SALUT}.",
     "en": "Crew, all passengers have left the aircraft. Thank you for this flight, and {SALUT}.",
     "de": "Liebe Crew, alle Passagiere haben das Flugzeug verlassen. Danke für diesen Flug, und {SALUT}.",
     "es": "Compañeros de tripulación, todos los pasajeros han abandonado la aeronave. Gracias por este vuelo, y {SALUT}."},
    {"fr": "Équipage, le débarquement est terminé. Merci de votre professionnalisme ; nous passons maintenant à la vérification de la cabine.",
     "en": "Crew, deboarding is now complete. Thank you for your professionalism; we will now move on to the cabin check.",
     "de": "Crew, der Ausstieg ist abgeschlossen. Danke für eure Professionalität; wir gehen nun zur Kabinenkontrolle über.",
     "es": "Tripulación, el desembarque ha finalizado. Gracias por su profesionalidad; procedemos ahora a la revisión de la cabina."},
    {"fr": "Équipage, la cabine est maintenant vide. Merci à toutes et à tous pour ce vol, et {SALUT}.",
     "en": "Crew, the cabin is now empty. Thank you all for this flight, and {SALUT}.",
     "de": "Crew, die Kabine ist jetzt leer. Danke euch allen für diesen Flug, und {SALUT}.",
     "es": "Tripulación, la cabina está ahora vacía. Gracias a todos por este vuelo, y {SALUT}."},
    {"fr": "Équipage, tous les passagers ont débarqué. Merci pour ce vol ; prochaine étape, la préparation de la cabine pour le vol suivant.",
     "en": "Crew, all passengers have deboarded. Thank you for this flight; next step is preparing the cabin for the next flight.",
     "de": "Crew, alle Passagiere sind ausgestiegen. Danke für diesen Flug; als Nächstes bereiten wir die Kabine für den nächsten Flug vor.",
     "es": "Tripulación, todos los pasajeros han desembarcado. Gracias por este vuelo; a continuación, preparamos la cabina para el próximo vuelo."},
])
add("Decompression", True, False, [
    {"fr": "Mesdames et messieurs, la pression dans la cabine a chuté. Restez calmes. Les masques à oxygène sont tombés. Tirez sur le masque le plus proche, placez-le sur le nez et la bouche, et respirez normalement. Restez assis, et suivez les instructions de l'équipage.",
     "en": "Ladies and gentlemen, the cabin pressure has dropped. Please remain calm. The oxygen masks have been released. Pull the nearest mask towards you, place it over your nose and mouth, and breathe normally. Remain seated, and follow the instructions of the crew.",
     "de": "Meine Damen und Herren, der Kabinendruck ist gefallen. Bleiben Sie ruhig. Die Sauerstoffmasken sind herabgefallen. Ziehen Sie an der nächsten Maske, setzen Sie sie auf Nase und Mund, und atmen Sie normal. Bleiben Sie sitzen, und folgen Sie den Anweisungen der Crew.",
     "es": "Señoras y señores, la presión en la cabina ha caído. Mantengan la calma. Las máscaras de oxígeno han caído. Tire de la máscara más cercana, colóquela sobre la nariz y la boca, y respire con normalidad. Permanezcan sentados, y sigan las instrucciones de la tripulación."},
    {"fr": "Mesdames et messieurs, nous avons une perte de pression en cabine. Les masques à oxygène sont tombés. Placez le masque sur votre visage, et respirez normalement. Si vous accompagnez un enfant, équipez-vous d'abord vous-même. Restez calmes et assis.",
     "en": "Ladies and gentlemen, we have lost cabin pressure. The oxygen masks have been released. Place the mask over your face, and breathe normally. If you are travelling with a child, fit your own mask first. Please remain calm and seated.",
     "de": "Meine Damen und Herren, wir haben einen Druckverlust in der Kabine. Die Sauerstoffmasken sind herabgefallen. Setzen Sie die Maske auf Ihr Gesicht, und atmen Sie normal. Wenn Sie ein Kind begleiten, setzen Sie zuerst Ihre eigene Maske auf. Bleiben Sie ruhig und sitzen.",
     "es": "Señoras y señores, hemos perdido presión en la cabina. Las máscaras de oxígeno han caído. Colóquese la máscara sobre el rostro, y respire con normalidad. Si acompaña a un niño, póngase primero su propia máscara. Mantengan la calma y permanezcan sentados."},
])

# ------------------------------------------------------------------ outils audio
FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    try:
        import imageio_ffmpeg
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG = "ffmpeg"
NOWIN = 0x08000000 if os.name == "nt" else 0


def ffmpeg(*args):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error"] + list(args), check=True, creationflags=NOWIN)


def fabrique_carillon(chemin):
    """Carillon cabine a deux notes (sol-mi, comme le "bong" Airbus), avec un
    soupcon d'harmonique et un battement leger pour eviter le son de synthese
    trop pur d'une sinusoide seule."""
    sr = 24000
    def ton(f, dur):
        n = int(sr * dur)
        enveloppe = lambda i: math.exp(-3.0 * i / sr) * (1 - math.exp(-60 * i / sr))
        out = []
        for i in range(n):
            e = enveloppe(i)
            fond = math.sin(2 * math.pi * f * i / sr)
            harmo = 0.12 * math.sin(2 * math.pi * (2 * f) * i / sr)
            battement = 0.03 * math.sin(2 * math.pi * (f + 1.5) * i / sr)
            out.append(0.45 * e * (fond + harmo + battement))
        return out
    s = ton(783.99, 1.0) + ton(659.25, 1.3)
    with wave.open(chemin, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in s))


async def tts(texte, voix, debit, hauteur, sortie, sem, essais_max=6, timeout_s=25):
    import edge_tts
    derniere = None
    for essai in range(essais_max):
        try:
            async with sem:
                c = edge_tts.Communicate(texte, voix, rate=debit, pitch=hauteur)
                await asyncio.wait_for(c.save(sortie), timeout=timeout_s)
            if os.path.getsize(sortie) > 2000:
                return True
        except Exception as e:
            derniere = e
        if essai < essais_max - 1:
            await asyncio.sleep(0.75 * (essai + 1))  # pause HORS semaphore : libere la place pour les autres
    print("  ECHEC voix", voix, derniere)
    return False


PA = ("highpass=f=400,equalizer=f=200:t=q:w=1:g=-8,lowpass=f=3000,equalizer=f=1500:t=q:w=1.2:g=4,"
      "acompressor=threshold=-14dB:ratio=1.3:attack=10:release=250,aecho=0.5:0.25:18:0.06,loudnorm=I=-26:TP=-3")


# bruit de fond mixe sous la voix, par phase de vol :
#  - embarquement (avant depart, moteurs pas encore demarres) : pas de bruit
#    moteur, juste un leger brouhaha de cabine (bruit "pink" dans la bande
#    vocale, module en amplitude pour evoquer des voix qui se chevauchent,
#    sans aucune parole reelle synthetisee ni echantillon enregistre) ;
#  - sol_moteurs (portes armees, check cabine avant le decollage, roulage a
#    l'arrivee) : moteurs demarres, ronronnement de reacteurs au ralenti ;
#  - montee : pleine poussee, le plus fort ;
#  - croisiere : stable et moyen ;
#  - descente/approche : reacteurs reduits.
# amplitude = niveau du bruit genere ; lp/hp = bande passante du filtrage.
PROFIL_BRUIT_FOND = {
    "embarquement": dict(color="pink",  amplitude=0.040, lp=2000, hp=200, tremolo=False),
    "sol_moteurs":  dict(color="brown", amplitude=0.030, lp=400,  hp=60,  tremolo=False),
    "montee":       dict(color="brown", amplitude=0.085, lp=700,  hp=50,  tremolo=False),
    "croisiere":    dict(color="brown", amplitude=0.045, lp=550,  hp=50,  tremolo=False),
    "descente":     dict(color="brown", amplitude=0.035, lp=500,  hp=50,  tremolo=False),
}
PHASE_PAR_TYPE = {
    # avant le depart, moteurs coupes : embarquement/debarquement, portes
    # desarmees a l'arrivee -> brouhaha de cabine, pas de bruit moteur.
    "BoardingWelcome": "embarquement", "BoardingComplete": "embarquement",
    "DisarmDoors": "embarquement", "DeboardingStarted": "embarquement",
    "DeboardingComplete": "embarquement",
    # portes armees, check cabine avant takeoff, roulage a l'arrivee : les
    # moteurs sont deja demarres.
    "ArmDoors": "sol_moteurs", "PreSafetyBriefing": "sol_moteurs",
    "SafetyBriefing": "sol_moteurs", "CrewTakeSeats": "sol_moteurs",
    "CabinDim": "sol_moteurs", "CabinSecured": "sol_moteurs", "AfterLanding": "sol_moteurs",
    "AfterTakeoff": "montee", "SeatbeltSignOff": "montee", "Decompression": "montee",
    "CabinService": "croisiere",
    "DescentStarted": "descente", "SeatbeltSignOn": "descente",
}


def assemble(clips, carillon, sortie_ogg, tmp, nom_type=""):
    """clips : liste d'un ou deux mp3 (langue principale, puis langue secondaire si presente).
    nom_type : nom du type d'annonce (ex. "AfterTakeoff"), utilisé pour choisir
    le profil de bruit de fond adapté à la phase de vol correspondante."""
    sil1, sil2 = os.path.join(tmp, "s1.wav"), os.path.join(tmp, "s2.wav")
    entrees = []
    def inp(p):
        entrees.extend(["-i", p]); return len(entrees) // 2 - 1
    idx = []
    if carillon:
        idx.append(inp(os.path.join(WORK, "carillon.wav"))); idx.append(inp(sil1))
    for i, clip in enumerate(clips):
        idx.append(inp(clip))
        if i < len(clips) - 1:
            idx.append(inp(sil2))
    profil = PROFIL_BRUIT_FOND[PHASE_PAR_TYPE.get(nom_type, "croisiere")]
    idx_bruit = len(entrees) // 2
    entrees.extend(["-f", "lavfi", "-i", "anoisesrc=color=%s:amplitude=%s:sample_rate=44100" % (profil["color"], profil["amplitude"])])
    f = ";".join("[%d:a]aresample=24000,aformat=channel_layouts=mono[a%d]" % (i, i) for i in idx)
    f += ";" + "".join("[a%d]" % i for i in idx) + "concat=n=%d:v=0:a=1,%s[voix]" % (len(idx), PA)
    # bruit de fond mixe sans normaliser (sinon amix diviserait aussi le
    # niveau de la voix par deux). tremolo = legere pulsation d'amplitude,
    # pour evoquer des voix qui se chevauchent (brouhaha) plutot qu'un bruit
    # constant et mecanique.
    f += ";[%d:a]lowpass=f=%d,highpass=f=%d" % (idx_bruit, profil["lp"], profil["hp"])
    if profil.get("tremolo"):
        f += ",tremolo=f=4:d=0.6"
    f += "[amb]"
    f += ";[voix][amb]amix=inputs=2:duration=first:normalize=0[o]"
    ffmpeg(*entrees, "-filter_complex", f, "-map", "[o]", "-ar", "44100", "-c:a", "libvorbis", "-q:a", "4", sortie_ogg)


def silence(chemin, dur):
    with wave.open(chemin, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(b"\x00\x00" * int(24000 * dur))


# ------------------------------------------------------------------ SimBrief
def lire_plan():
    url = "https://www.simbrief.com/api/xml.fetcher.php?userid=%s&json=1" % SIMBRIEF_ID
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


# ------------------------------------------------------------------ génération
async def genere(profils, types, ctx, sortie_dir):
    """types = liste d'entrées T ; écrit sortie_dir/<Type>[n].ogg"""
    os.makedirs(sortie_dir, exist_ok=True)
    tmpb = os.path.join(WORK, "tmp"); os.makedirs(tmpb, exist_ok=True)
    silence(os.path.join(tmpb, "s1.wav"), 0.35); silence(os.path.join(tmpb, "s2.wav"), 0.6)
    sem = asyncio.Semaphore(NB_PARALLELE)
    sem2 = asyncio.Semaphore(4)
    ok = 0; total = 0; fini = 0; dernier_pct = [-100]
    echoues = []
    def _progres():
        if total <= 0:
            return
        pct = int(fini * 100 / total)
        if pct - dernier_pct[0] >= 5 or fini == total:
            dernier_pct[0] = pct
            print("Progression : %d%% (%d/%d) / Progress: %d%% (%d/%d)" % (pct, fini, total, pct, fini, total))
    async def une(num, prof, ti, entree, repasse=False):
        nonlocal ok, fini
        nom, carillon, perso, variantes = entree
        cle = "%s_%02d" % (nom, num)
        tmp = os.path.join(tmpb, cle)
        try:
            texte = variantes[(num + ti) % len(variantes)]
            v_prim, v_sec, debit, haut = prof
            os.makedirs(tmp, exist_ok=True)
            primaire_t = texte[LANG].format(**ctx[LANG])
            clips = []
            complet = True
            sem_choisi = sem2 if repasse else sem
            a = await tts(primaire_t, v_prim, debit, haut, os.path.join(tmp, "p.mp3"), sem_choisi)
            if a:
                clips.append(os.path.join(tmp, "p.mp3"))
            else:
                complet = False
            if SECONDE_LANGUE and v_sec:
                sec_t = texte[SECONDE_LANGUE].format(**ctx[SECONDE_LANGUE])
                b = await tts(sec_t, v_sec, debit, haut, os.path.join(tmp, "s.mp3"), sem_choisi)
                if b:
                    clips.append(os.path.join(tmp, "s.mp3"))
                else:
                    complet = False
            if complet and clips:
                sortie = os.path.join(sortie_dir, "%s[%d].ogg" % (nom, num))
                await asyncio.get_event_loop().run_in_executor(None, assemble, clips, carillon, sortie, tmpb, nom)
                ok += 1
            else:
                echoues.append((num, prof, ti, entree))
        except Exception as e:
            print("  ECHEC clip %s : %r" % (cle, e))
            echoues.append((num, prof, ti, entree))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            if not repasse:
                fini += 1
                _progres()
    taches = []
    for ti, entree in enumerate(T):
        if entree not in types:
            continue
        for num, prof in enumerate(profils, start=1):
            taches.append(une(num, prof, ti, entree)); total += 1
    resultats = await asyncio.gather(*taches, return_exceptions=True)
    echecs = [r for r in resultats if isinstance(r, Exception)]
    if echecs:
        print("  (%d tache(s) ont leve une exception inattendue malgre la protection interne)" % len(echecs))

    tour = 0
    while echoues and tour < 3:
        tour += 1
        a_retenter = echoues
        echoues = []
        print("Nouvelle tentative (tour %d) pour %d annonce(s) / Retry pass %d for %d announcement(s)"
              % (tour, len(a_retenter), tour, len(a_retenter)))
        await asyncio.sleep(2)
        taches2 = [une(num, prof, ti, entree, repasse=True) for (num, prof, ti, entree) in a_retenter]
        await asyncio.gather(*taches2, return_exceptions=True)

    return ok, total


async def profils_valides():
    """garde les profils dont les voix repondent (la 2e voix peut etre absente en mode anglais seul)."""
    tmp = os.path.join(WORK, "tmp"); os.makedirs(tmp, exist_ok=True)
    res = {}
    sem_test = asyncio.Semaphore(6)
    async def test(v):
        if v is None or v in res:
            return
        p = os.path.join(tmp, "t_%s.mp3" % v)
        res[v] = await tts("Bonjour, bienvenue a bord.", v, "+0%", "+0Hz", p, sem_test)
    await asyncio.gather(*[test(v) for prof in PROFILS for v in (prof[0], prof[1]) if v is not None])
    return [p for p in PROFILS if res.get(p[0]) and (p[1] is None or res.get(p[1]))], res


def ecrit_layout():
    contenu = []
    def fichier(chemin):
        st = os.stat(chemin)
        contenu.append({"path": os.path.relpath(chemin, PKG).replace("\\", "/"), "size": st.st_size,
                        "date": int((st.st_mtime + 11644473600) * 10000000)})
    for racine, _, fs in os.walk(PKG):
        for f in fs:
            if f != "layout.json":
                fichier(os.path.join(racine, f))
    with open(os.path.join(PKG, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump({"content": contenu}, fh, indent=2)


def ecrit_manifest():
    os.makedirs(PKG, exist_ok=True)
    m = {"dependencies": [], "content_type": "MISC", "title": "Cabin announcements (Fenix A320 airline packs)",
         "manufacturer": "Cleardeck Studio", "creator": "Cleardeck Studio", "package_version": "1.0.0", "minimum_game_version": "1.0.0",
         "release_notes": {"neutral": {"LastUpdate": "", "OlderHistory": ""}}}
    with open(os.path.join(PKG, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2)


def publie(src_dir):
    """copie le contenu de src_dir vers AirlinePacks/<code> pour chaque code."""
    ecrit_manifest()
    for code in CODES:
        dst = os.path.join(PKG, "AirlinePacks", code)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src_dir):
            shutil.copy2(os.path.join(src_dir, f), os.path.join(dst, f))
    ecrit_layout()


def ecrit_etat(d):
    with open(os.path.join(WORK, "etat.json"), "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    js = os.path.join(HERE, "pack_cabine_etat.js")
    with open(js, "w", encoding="utf-8") as fh:
        fh.write("window.PACK_CABINE=" + json.dumps(d, ensure_ascii=False) + ";\n")


def lit_etat():
    try:
        return json.load(open(os.path.join(WORK, "etat.json"), encoding="utf-8"))
    except Exception:
        return {}


def msfs_actif():
    try:
        r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=20, creationflags=NOWIN)
        return "flightsimulator2024.exe" in (r.stdout or "").lower()
    except Exception:
        return False


def metar_frais(icao):
    """METAR actuel (aviationweather.gov, gratuit) ; None si injoignable."""
    try:
        req = urllib.request.Request("https://aviationweather.gov/api/data/metar?ids=%s&format=raw" % icao, headers={"User-Agent": "carriere-cabine/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            lignes = [x.strip() for x in r.read().decode("utf-8", "replace").splitlines() if x.strip()]
        return lignes[0] if lignes and icao in lignes[0] else None
    except Exception:
        return None


def signature_meteo(m):
    return "%s|%s|%s|%s" % (m["temp"], m["kt"] // 4, m["sky"], ",".join(sorted(m["wx"])))


def combler(tout, profils):
    """pas de trou dans la numérotation des variantes : une variante manquante est remplacée par la n°1"""
    for entree in T:
        for n in range(1, len(profils) + 1):
            cible = os.path.join(tout, "%s[%d].ogg" % (entree[0], n))
            if not os.path.exists(cible):
                src = os.path.join(tout, "%s[1].ogg" % entree[0])
                if os.path.exists(src):
                    shutil.copy2(src, cible)
                    print("  variante comblée :", os.path.basename(cible))


def publie_selection(profils, ctx, noms):
    sel = [e for e in T if e[0] in noms]
    dossier = os.path.join(WORK, "sel")
    shutil.rmtree(dossier, ignore_errors=True)
    ok, tot = asyncio.run(genere(profils, sel, ctx, dossier))
    tout = os.path.join(WORK, "assemble")
    os.makedirs(tout, exist_ok=True)
    for f in os.listdir(dossier):
        shutil.copy2(os.path.join(dossier, f), os.path.join(tout, f))
    combler(tout, profils)
    publie(tout)
    return ok, tot


def types_meteo(marqueurs):
    """noms des annonces dont le texte cite la météo (marqueurs {TEMP_D…} ou {TEMP_O…})"""
    def textes(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for y in x.values():
                yield from textes(y)
        elif isinstance(x, (list, tuple)):
            for y in x:
                yield from textes(y)
    return [e[0] for e in T if any(m in t for t in textes(e[3]) for m in marqueurs)]


def executer(argv):
    args = set(a for a in argv if not a.startswith("--types="))
    noms = []
    for a in argv:
        if a.startswith("--types="):
            noms = [x for x in a[8:].split(",") if x]
    os.makedirs(WORK, exist_ok=True)
    fabrique_carillon(os.path.join(WORK, "carillon.wav"))
    verrou = os.path.join(WORK, "verrou.txt")
    if os.path.exists(verrou) and time.time() - os.path.getmtime(verrou) < 1800:
        print("Une génération est déjà en cours (déjà lancée)."); return
    open(verrou, "w").write(str(os.getpid()))
    statut = os.path.join(WORK, "_STATUT_INSTALLATION.txt")
    def _statut(texte):
        try:
            with open(statut, "w", encoding="utf-8") as f:
                f.write(texte + "\n" + time.strftime("%d/%m/%Y %H:%M:%S"))
        except Exception:
            pass
    try:
        if "--test-voix" in args:
            profils, res = asyncio.run(profils_valides())
            for p in PROFILS:
                print("OK " if (res[p[0]] and res[p[1]]) else "KO ", p)
            print(len(profils), "profils sur", len(PROFILS)); return
        plan = lire_plan()
        cle = str(plan["params"]["time_generated"])
        etat = lit_etat()
        icao_o, icao_d = plan["origin"]["icao_code"], plan["destination"]["icao_code"]
        mode = None
        if noms:
            mode = "types"
        elif "--tout" in args or "--vol" in args or etat.get("plan") != cle:
            mode = "vol"
        elif "--meteo" in args and msfs_actif() and time.time() - etat.get("meteo_t", 0) >= 600:
            m_d = metar_frais(icao_d)
            nouvelle = time.time() - etat.get("meteo_t", 0) > 3 * 3600      # premier contrôle d'une nouvelle session de simulateur
            etat["meteo_t"] = time.time()
            if m_d and (nouvelle or signature_meteo(parse_metar(m_d)) != etat.get("meteo_sig")):
                mode = "meteo"
                etat["meteo_origine"] = nouvelle
            else:
                ecrit_etat(etat); print("Météo inchangée (déjà vérifiée)."); return
        if mode is None:
            print("Plan déjà traité."); return
        profils, res = asyncio.run(profils_valides())
        # --- un seul chef de cabine (meme voix) pendant tout le vol : on fixe UNE
        # voix (choisie au hasard a chaque reinstallation complete du pack - mode
        # "vol" - sinon on reutilise celle deja choisie pour ce vol, memorisee dans
        # etat.json, pour que les mises a jour meteo/types gardent la meme voix) ---
        profil_fixe = next((p for p in profils if p[0] == etat.get("voix_chef_cabine")), None)
        if mode == "vol" or profil_fixe is None:
            profil_fixe = random.choice(profils) if profils else None
        profils_pack = [profil_fixe] * len(profils) if profil_fixe else profils
        m_o, m_d = metar_frais(icao_o), metar_frais(icao_d)
        ctx = contexte(plan, m_o, m_d)
        sig = signature_meteo(parse_metar(m_d or plan["destination"].get("metar")))
        print("Vol", plan["general"].get("icao_airline"), plan["general"].get("flight_number"), icao_o, "->", icao_d,
              "|", len(profils), "profils | voix:", (profil_fixe[0] if profil_fixe else "?"), "| mode", mode,
              "| METAR", "frais" if m_d else "du plan SimBrief")
        print("=" * 70)
        print("INSTALLATION EN COURS - NE FERMEZ PAS CETTE FENETRE")
        print("INSTALLATION IN PROGRESS - DO NOT CLOSE THIS WINDOW")
        print("=" * 70)
        _statut("EN COURS - ne fermez pas la fenetre / IN PROGRESS - do not close the window")
        t0 = time.time()
        if mode == "types":
            ok, tot = publie_selection(profils_pack, ctx, noms)
            print("régénéré :", ok, "/", tot)
            ecrit_etat(dict(etat, quand=time.strftime("%d/%m/%Y %H:%M")))
        elif mode == "meteo":
            a_faire = types_meteo(("{TEMP_D", "{SKY_D", "{WIND_D", "{COMMENT_D"))
            if etat.get("meteo_origine"):
                a_faire += [n for n in types_meteo(("{TEMP_O", "{SKY_O", "{WIND_O", "{COMMENT_O")) if n not in a_faire]
            ok, tot = publie_selection(profils_pack, ctx, a_faire)
            print("météo mise à jour (%s) :" % ", ".join(a_faire), ok, "/", tot)
            ecrit_etat(dict(etat, meteo_sig=sig, meteo_t=time.time(), meteo_origine=False, metar_d=m_d, metar_o=m_o, quand=time.strftime("%d/%m/%Y %H:%M")))
        else:
            generique = os.path.join(WORK, "generique"); perso = os.path.join(WORK, "vol")
            noms_generiques = {e[0] for e in T if not e[2]}
            presents = set()
            if os.path.isdir(generique):
                for f in os.listdir(generique):
                    presents.add(f.split("[", 1)[0])
            incomplet = noms_generiques - presents
            if incomplet:
                print("  types generiques manquants detectes (regeneration complete) :", ", ".join(sorted(incomplet)))
            if "--tout" in args or not os.path.isdir(generique) or incomplet:
                shutil.rmtree(generique, ignore_errors=True)
                ok, tot = asyncio.run(genere(profils_pack, [e for e in T if not e[2]], ctx, generique))
                print("génériques :", ok, "/", tot)
            shutil.rmtree(perso, ignore_errors=True)
            ok, tot = asyncio.run(genere(profils_pack, [e for e in T if e[2]], ctx, perso))
            print("du vol :", ok, "/", tot)
            tout = os.path.join(WORK, "assemble"); shutil.rmtree(tout, ignore_errors=True); os.makedirs(tout)
            for d in (generique, perso):
                for f in os.listdir(d):
                    shutil.copy2(os.path.join(d, f), os.path.join(tout, f))
            combler(tout, profils_pack)
            publie(tout)
            ecrit_etat({"plan": cle, "vol": "%s%s" % (plan["general"].get("icao_airline", ""), plan["general"].get("flight_number", "")),
                        "de": icao_o, "vers": icao_d, "nb_profils": len(profils), "fichiers": len(os.listdir(tout)),
                        "voix_chef_cabine": profil_fixe[0] if profil_fixe else None,
                        "quand": time.strftime("%d/%m/%Y %H:%M"), "duree_s": int(time.time() - t0),
                        "meteo_sig": sig, "meteo_t": time.time(), "metar_d": m_d})
        print("Pack publié dans", PKG, "en", int(time.time() - t0), "s")
        print("=" * 70)
        print("INSTALLATION TERMINEE - vous pouvez fermer cette fenetre / lancer MSFS")
        print("INSTALLATION COMPLETE - you can close this window / start MSFS")
        print("=" * 70)
        _statut("TERMINE / COMPLETE")
    except Exception:
        _statut("ERREUR - voir le message ci-dessus dans la console / ERROR - see the message above in the console")
        raise
    finally:
        try: os.remove(verrou)
        except Exception: pass


def _attendre(secondes, arreter):
    """Attend 'secondes' secondes, en verifiant 'arreter' chaque seconde pour
    pouvoir stopper rapidement depuis l'interface graphique. arreter est un
    threading.Event, ou None en mode console (Ctrl+C suffit alors)."""
    for _ in range(int(secondes)):
        if arreter is not None and arreter.is_set():
            return
        time.sleep(1)


# Nom canonique par code ICAO compagnie : le champ atc_airline ecrit a la main
# par le createur d'une livree est parfois fantaisiste ou deforme (ex. le
# livery.cfg de la livree Air France F-HEPH ecrit "Airfrans" au lieu de "Air
# France", sans doute pour eviter toute mention directe de la marque dans le
# fichier). Le code ICAO (icao_airline), lui, est fiable : on privilegie donc
# ce nom canonique quand on connait le code, pour que la prononciation ET la
# bibliotheque SERVICES_BORD (qui est indexee sur le nom, pas sur le code)
# retombent correctement sur la bonne compagnie.
NOM_COMPAGNIE_PAR_ICAO = {
    "EWG": "Eurowings",
    "EWE": "Eurowings Europe",
    "TRA": "Transavia",
    "TVF": "Transavia",
    "AFR": "Air France",
    "DLH": "Lufthansa",
    "BAW": "British Airways",
    "EZY": "easyJet",
    "EJU": "easyJet",
}


JOURNAL_PATH = os.path.join(HERE, "debug_simconnect.log")


def _journal(msg):
    """Ecrit une ligne horodatee dans debug_simconnect.log, a cote de
    config_cabine.json. La fenetre console de l'exe etant masquee pour les
    simmers, ce fichier permet de diagnostiquer la detection SimConnect a
    distance sans avoir besoin de voir la console. Best-effort, ne doit
    jamais faire planter l'appelant ; tronque le fichier s'il devient trop
    gros pour rester lisible."""
    try:
        ligne = "%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
        if os.path.exists(JOURNAL_PATH) and os.path.getsize(JOURNAL_PATH) > 200_000:
            with open(JOURNAL_PATH, "r", encoding="utf-8", errors="ignore") as f:
                reste = f.read()[-100_000:]
            with open(JOURNAL_PATH, "w", encoding="utf-8") as f:
                f.write(reste)
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(ligne)
    except Exception:
        pass


# Connexion SimConnect deja etablie et entretenue par surveillance_simconnect()
# (si la boucle de surveillance tourne). contexte() la reutilise en priorite
# pour lire ZULU_TIME au lieu d'ouvrir une 2e connexion concurrente avec un
# timeout court, qui echouait silencieusement (cf. bug heure non prise en
# compte - repli errone sur l'heure PREVUE du plan SimBrief).
_AQ_SIMCONNECT_ACTIF = None


def livree_active_via_simconnect(aq, community):
    """Lit l'immatriculation (ATC ID) de l'avion actuellement charge dans le
    simulateur via SimConnect, et la fait correspondre a l'une des livrees
    installees (detectees par scanner_livrees_fenix). Retourne le dict de la
    livree correspondante (nom, compagnie, icao, immat, chemin) si trouvee,
    sinon None - permet de reconnaitre automatiquement la compagnie au
    demarrage du vol, sans selection manuelle."""
    try:
        immat_brute = aq.get("ATC_ID")
    except Exception as ex:
        _journal("ATC_ID : exception a la lecture SimConnect : %r" % ex)
        return None
    if not immat_brute:
        _journal("ATC_ID : valeur vide/None renvoyee par SimConnect (%r)" % (immat_brute,))
        return None
    # le wrapper SimConnect renvoie l'ATC_ID en bytes (b'F-HEPH') : un str()
    # direct produit le texte litteral "b'F-HEPH'" (avec le prefixe b et les
    # quotes) au lieu de decoder la valeur, donc la comparaison avec
    # l'immatriculation propre lue dans livery.cfg echouait toujours. On
    # decode explicitement si c'est du bytes, puis on enleve en plus
    # d'eventuels octets nuls de bourrage de fin de buffer (que .strip() seul
    # n'enleve pas, ce ne sont pas des espaces).
    if isinstance(immat_brute, (bytes, bytearray)):
        immat = immat_brute.decode("utf-8", "ignore")
    else:
        immat = str(immat_brute)
    immat = immat.replace("\x00", "").strip().strip('"').upper()
    if not immat:
        _journal("ATC_ID : vide apres nettoyage (brut=%r)" % (immat_brute,))
        return None
    livrees = scanner_livrees_fenix(community)
    for livree in livrees:
        if (livree.get("immat") or "").strip().upper() == immat:
            _journal("ATC_ID %r (brut=%r) -> correspondance trouvee : %s / %s / immat %s" %
                      (immat, immat_brute, livree.get("compagnie"), livree.get("icao"), livree.get("immat")))
            return livree
    # aucune correspondance : on journalise l'immat lue et celles connues,
    # pour diagnostiquer facilement un futur cas de non-detection.
    _journal("ATC_ID %r (brut=%r) sans correspondance parmi %d livree(s) scannee(s) : %s" %
              (immat, immat_brute, len(livrees), [(l.get("compagnie"), l.get("icao"), l.get("immat")) for l in livrees]))
    return None


def surveillance_simconnect(arreter=None):
    """Boucle de surveillance automatique via SimConnect : tant qu'un vol est
    detecte dans la simulation (MSFS lance ET un avion charge, pas juste le
    menu principal), regenere les annonces du vol et la meteo automatiquement
    - equivalent de --boucle, mais declenche par l'etat reel du simulateur
    plutot que par une simple minuterie. arreter (threading.Event) permet de
    stopper la boucle depuis l'interface graphique ; en mode console, Ctrl+C
    fonctionne aussi. A chaque vol detecte, tente aussi de reconnaitre
    automatiquement la compagnie via l'immatriculation de la livree active
    (livree_active_via_simconnect) : si elle correspond a une livree
    installee, COMPAGNIE/CODES sont mis a jour automatiquement, sans
    selection manuelle dans l'interface."""
    global COMPAGNIE, CODES, _AQ_SIMCONNECT_ACTIF
    print("=" * 70)
    print("%s - surveillance SimConnect (automatique)" % NOM_PRODUIT)
    print("Connexion a SimConnect... (necessite que MSFS 2024 soit lance)")
    print("Fermez cette fenetre pour arreter. Ctrl+C fonctionne aussi.")
    print("=" * 70)
    sm = None
    aq = None
    en_vol_avant = None
    echecs = 0
    livree_detectee_pour = None
    while True:
        if arreter is not None and arreter.is_set():
            print("Arret demande.")
            break
        try:
            if sm is None:
                try:
                    from SimConnect import SimConnect, AircraftRequests
                    sm = SimConnect()
                    aq = AircraftRequests(sm, _time=2000)
                    _AQ_SIMCONNECT_ACTIF = aq
                    print("Connecte a SimConnect.")
                    _journal("Connecte a SimConnect.")
                except Exception as e:
                    print("SimConnect indisponible (%r). MSFS 2024 est-il lance ? Nouvel essai dans 15s." % e)
                    _journal("SimConnect indisponible : %r" % e)
                    sm = None
                    _AQ_SIMCONNECT_ACTIF = None
                    aq = None
                    _attendre(15, arreter)
                    continue

            en_vol = aq.get("SIM_ON_GROUND") is not None
            if en_vol:
                echecs = 0
                compagnie_vient_de_changer = False
                if en_vol_avant is not True:
                    print("Vol detecte (SimConnect connecte a la simulation).")
                    _journal("Vol detecte (SIM_ON_GROUND non-None).")
                    livree_detectee_pour = None
                if livree_detectee_pour != True:
                    try:
                        livree = livree_active_via_simconnect(aq, COMMUNITY)
                    except Exception as ex:
                        livree = None
                        print("[SimConnect] detection livree impossible : %r" % ex)
                    if livree:
                        _icao_livree = (livree.get("icao") or "").upper()
                        nouvelle_compagnie = NOM_COMPAGNIE_PAR_ICAO.get(_icao_livree) or livree.get("compagnie") or COMPAGNIE
                        nouveaux_codes = [livree.get("icao")] if livree.get("icao") else CODES
                        if nouvelle_compagnie != COMPAGNIE or nouveaux_codes != CODES:
                            COMPAGNIE = nouvelle_compagnie
                            CODES = nouveaux_codes
                            compagnie_vient_de_changer = True
                            try:
                                cfg = _charge_config()
                                cfg["compagnie"] = COMPAGNIE
                                cfg["codes_compagnie"] = ",".join(CODES)
                                _sauve_config(cfg)
                            except Exception:
                                pass
                            print("Livree active reconnue automatiquement : %s (%s, immat %s)." %
                                  (COMPAGNIE, CODES[0] if CODES else "?", livree.get("immat") or "?"))
                        livree_detectee_pour = True
                try:
                    # si la compagnie detectee vient de changer (nouvelle livree chargee
                    # pour le meme plan SimBrief), --auto seul ne regenere rien (le plan
                    # n'a pas change a ses yeux) : on force --vol pour regenerer tout de
                    # suite le pack de la compagnie nouvellement identifiee.
                    executer(["--vol" if compagnie_vient_de_changer else "--auto", "--meteo"])
                except Exception as ex:
                    print("[SimConnect] erreur generation : %r" % ex)
                en_vol_avant = True
                _attendre(60, arreter)
            else:
                echecs += 1
                if en_vol_avant is not False:
                    print("En attente d'un vol (menu principal, ou simulation pas encore chargee)...")
                en_vol_avant = False
                if echecs >= 10:
                    sm = None
                    aq = None
                    _AQ_SIMCONNECT_ACTIF = None
                    echecs = 0
                _attendre(15, arreter)
        except KeyboardInterrupt:
            print("Arret demande.")
            break
        except Exception as ex:
            print("[SimConnect] erreur boucle (on reessaie dans 15s) : %r" % ex)
            _attendre(15, arreter)
    _AQ_SIMCONNECT_ACTIF = None
    try:
        if sm:
            sm.exit()
    except Exception:
        pass


def detecter_gsx_installe(community):
    """GSX Pro est installe des que son paquet de base 'fsdreamteam-gsx-pro'
    est present dans Community (les paquets associes - EFB, World of
    Jetways, VDGS - ne viennent jamais sans lui)."""
    if not community or not os.path.isdir(community):
        return False
    return os.path.isdir(os.path.join(community, "fsdreamteam-gsx-pro"))


def detecter_module_mobiflight(community):
    """Le pont MobiFlight (necessaire pour lire en direct les LVars GSX
    d'embarquement/debarquement depuis ce programme) est installe des que
    son fichier .wasm est present dans Community."""
    if not community or not os.path.isdir(community):
        return False
    return os.path.isfile(os.path.join(community, "mobiflight-event-module", "modules", "MobiFlightWasmModule.wasm"))


def installer_module_mobiflight_si_necessaire(community, log=print):
    """Installe automatiquement le module MobiFlight (pont GSX <-> SimConnect,
    une copie officielle embarquee avec ce programme) si GSX Pro est
    installe mais que ce pont manque - sans lui, les annonces en direct au
    commandant (debut/fin embarquement et debarquement) restent muettes.
    Ne fait rien si GSX n'est pas installe (inutile), ni si le module est
    deja present (on ne touche jamais a une installation existante).
    Jamais bloquant : une erreur ici n'empeche pas le reste de l'installation.
    Renvoie : 'gsx_absent', 'deja_present', 'installe', 'source_introuvable' ou 'erreur'."""
    try:
        if not detecter_gsx_installe(community):
            return "gsx_absent"
        if detecter_module_mobiflight(community):
            return "deja_present"
        source = _recurso("mobiflight_module")
        if not os.path.isdir(source):
            log("Module MobiFlight : fichiers source introuvables dans le programme (installation manuelle necessaire).")
            return "source_introuvable"
        dest = os.path.join(community, "mobiflight-event-module")
        for racine, _dossiers, fichiers in os.walk(source):
            rel = os.path.relpath(racine, source)
            cible_dir = os.path.join(dest, rel) if rel != "." else dest
            os.makedirs(cible_dir, exist_ok=True)
            for f in fichiers:
                shutil.copy2(os.path.join(racine, f), os.path.join(cible_dir, f))
        return "installe"
    except Exception as e:
        log("Module MobiFlight : installation automatique impossible (%r) ; vous pouvez l'installer manuellement via MobiFlight Connector." % e)
        return "erreur"


def _chemin_exe_xml():
    """Retrouve EXE.xml de MSFS 2024 a partir du dossier Community choisi
    (meme principe que pour Carriere/Copilote sur ce PC) :
    - version Microsoft Store : ...\\LocalCache\\Packages\\Community -> ...\\LocalCache\\EXE.xml
    - version Steam/Boite     : ...\\Microsoft Flight Simulator 2024\\Community -> ...\\exe.xml
    Renvoie None si le dossier Community ne ressemble a aucun des deux."""
    c = (COMMUNITY or "").replace("/", "\\")
    bas = c.lower()
    repere1 = "\\packages\\community"
    i = bas.find(repere1)
    if i != -1:
        return c[:i] + "\\EXE.xml"
    repere2 = "\\community"
    i = bas.rfind(repere2)
    if i != -1:
        return c[:i] + "\\exe.xml"
    return None


def inscrire_exe_xml():
    """Ajoute (ou met a jour) une entree dans EXE.xml de MSFS pour que ce
    programme soit lance automatiquement avec --auto-msfs a chaque demarrage
    de MSFS 2024, et se ferme tout seul avec lui. Ne touche a rien d'autre
    dans le fichier ; sans effet (silencieux) si EXE.xml est introuvable ou
    illisible - ce n'est jamais bloquant pour l'installation du pack vocal."""
    chemin = _chemin_exe_xml()
    if not chemin:
        return False, "Dossier Community non reconnu (MSFS introuvable automatiquement)."
    exe = _sys.executable if getattr(_sys, "frozen", False) else os.path.abspath(_sys.argv[0])
    nom_addon = NOM_PRODUIT
    bloc = (
        "  <Launch.Addon>\n"
        "    <Name>%s</Name>\n"
        "    <Disabled>False</Disabled>\n"
        "    <ManualLoad>False</ManualLoad>\n"
        "    <Path>%s</Path>\n"
        "    <CommandLine>--auto-msfs</CommandLine>\n"
        "    <NewConsole>False</NewConsole>\n"
        "  </Launch.Addon>\n"
    ) % (nom_addon, exe)
    try:
        if os.path.isfile(chemin):
            for enc in ("utf-8-sig", "cp1252", "latin-1"):
                try:
                    with open(chemin, encoding=enc) as f:
                        texte = f.read()
                    break
                except Exception:
                    texte = None
            if texte is None:
                return False, "EXE.xml illisible (encodage)."
            try:
                shutil.copyfile(chemin, chemin + ".bak_avant_eurowings")
            except Exception:
                pass
            # migration : retire toute ancienne entree enregistree sous un
            # nom de produit precedent (renommage), pour eviter un doublon
            # d'auto-lancement a cote de la nouvelle entree.
            for ancien_nom in NOMS_PRODUIT_ANCIENS:
                d = texte.find("<Name>%s</Name>" % ancien_nom)
                if d != -1:
                    aa = texte.rfind("<Launch.Addon>", 0, d)
                    bb = texte.find("</Launch.Addon>", d)
                    if aa != -1 and bb != -1:
                        bb += len("</Launch.Addon>")
                        if texte[bb:bb + 1] == "\n":
                            bb += 1
                        texte = texte[:aa] + texte[bb:]
            debut = texte.find("<Name>%s</Name>" % nom_addon)
            if debut != -1:
                a = texte.rfind("<Launch.Addon>", 0, debut)
                b = texte.find("</Launch.Addon>", debut)
                if a != -1 and b != -1:
                    b += len("</Launch.Addon>")
                    texte = texte[:a] + bloc.strip("\n") + texte[b:]
                else:
                    texte = texte.replace("</SimBase.Document>", bloc + "</SimBase.Document>")
            else:
                if "</SimBase.Document>" in texte:
                    texte = texte.replace("</SimBase.Document>", bloc + "</SimBase.Document>")
                else:
                    return False, "Format EXE.xml non reconnu."
        else:
            texte = (
                '<?xml version="1.0" encoding="windows-1252"?>\n'
                "<SimBase.Document Type=\"SimConnect\" version=\"1,0\">\n"
                "  <Descr>SimConnect</Descr>\n"
                "  <Filename>SimConnect.xml</Filename>\n"
                "  <Disabled>False</Disabled>\n"
                + bloc +
                "</SimBase.Document>\n"
            )
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(texte)
        return True, chemin
    except Exception as e:
        return False, repr(e)


def _msfs_tourne():
    """True si FlightSimulator2024.exe tourne encore (ou si on ne peut pas
    savoir : on prefere alors ne pas fermer le programme trop vite)."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq FlightSimulator2024.exe"],
            creationflags=0x08000000)
        texte = out.decode("utf-8", "ignore")
        return "FlightSimulator2024.exe" in texte
    except Exception:
        return True


PORT_SERVEUR_CONFIG = 58734


def _demarre_serveur_config_toolbar(arreter):
    """Petit serveur HTTP local pour le panneau de la barre d'outils MSFS
    (CabinConfig) : GET /config lit la config courante, POST /config
    l'ecrit et met a jour les variables globales (compagnie, codes ICAO,
    langue, nom d'equipage) sans qu'il faille redemarrer le programme."""
    import http.server
    import socketserver

    class Gestionnaire(http.server.BaseHTTPRequestHandler):
        def _entetes_cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _repond_json(self, code, obj):
            corps = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self._entetes_cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            try:
                self.wfile.write(corps)
            except Exception:
                pass

        def do_OPTIONS(self):
            self.send_response(204)
            self._entetes_cors()
            self.end_headers()

        def do_GET(self):
            if self.path.split("?", 1)[0].rstrip("/") != "/config":
                self._repond_json(404, {"erreur": "introuvable"})
                return
            self._repond_json(200, {
                "compagnie": COMPAGNIE,
                "codes_compagnie": ",".join(CODES),
                "langue": LANG,
                "nom_equipage": NOM_EQUIPAGE,
                "simbrief_id": SIMBRIEF_ID,
            })

        def do_POST(self):
            if self.path.split("?", 1)[0].rstrip("/") != "/config":
                self._repond_json(404, {"erreur": "introuvable"})
                return
            global COMPAGNIE, CODES, LANG, SECONDE_LANGUE, PROFILS, NOM_EQUIPAGE, SIMBRIEF_ID
            try:
                taille = int(self.headers.get("Content-Length", "0") or "0")
                brut = self.rfile.read(taille) if taille > 0 else b"{}"
                entree = json.loads(brut.decode("utf-8") or "{}")
            except Exception:
                entree = {}

            compagnie_nouvelle = str(entree.get("compagnie") or COMPAGNIE).strip() or COMPAGNIE
            codes_txt = str(entree.get("codes_compagnie") or ",".join(CODES))
            codes_nouveaux = [c.strip().upper() for c in codes_txt.split(",") if c.strip()] or CODES
            langue_nouvelle = str(entree.get("langue") or LANG).strip().lower()
            if langue_nouvelle not in {v[0] for v in LANGUES.values()}:
                langue_nouvelle = LANG
            simbrief_nouveau = str(entree.get("simbrief_id") or SIMBRIEF_ID).strip()
            if not simbrief_nouveau.isdigit():
                simbrief_nouveau = SIMBRIEF_ID

            COMPAGNIE = compagnie_nouvelle
            CODES = codes_nouveaux
            LANG = langue_nouvelle
            SECONDE_LANGUE = None if LANG == "en" else "en"
            PROFILS = PROFILS_PAR_LANGUE[LANG]
            NOM_EQUIPAGE = prenom_chef_cabine_aleatoire(LANG)
            SIMBRIEF_ID = simbrief_nouveau

            cfg = _charge_config()
            cfg["compagnie"] = COMPAGNIE
            cfg["codes_compagnie"] = ",".join(CODES)
            cfg["langue"] = LANG
            cfg["nom_equipage"] = NOM_EQUIPAGE
            cfg["simbrief_id"] = SIMBRIEF_ID
            try:
                _sauve_config(cfg)
            except Exception:
                pass

            self._repond_json(200, {"ok": True})

        def log_message(self, format, *args):
            pass  # pas de bruit dans la console du programme

    try:
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT_SERVEUR_CONFIG), Gestionnaire)
        httpd.daemon_threads = True
    except Exception as e:
        print("Serveur config (barre d'outils) : impossible de demarrer (%s)." % e)
        return

    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def _arrete_avec_programme():
        arreter.wait()
        try:
            httpd.shutdown()
        except Exception:
            pass

    threading.Thread(target=_arrete_avec_programme, daemon=True).start()
    print("Serveur config (barre d'outils) actif sur http://127.0.0.1:%d/config" % PORT_SERVEUR_CONFIG)


# ------------------------------------------------------------------ GSX (embarquement/debarquement en direct)
ANNONCES_GSX = {
    "fr": {"boarding_start": "Commandant, l'embarquement commence.",
           "boarding_start_prevu": "Commandant, l'embarquement commence. Nous attendons {prevu} passagers.",
           "boarding_done_ok": "Commandant, l'embarquement est termine. Nous avons {n} passagers a bord, conforme au plan de vol.",
           "boarding_done_diff": "Commandant, l'embarquement est termine. Nous avons {n} passagers a bord, contre {prevu} prevus.",
           "boarding_done_nosb": "Commandant, l'embarquement est termine. Nous avons {n} passagers a bord.",
           "deboarding_start": "Commandant, le debarquement commence.",
           "deboarding_done": "Commandant, tous les passagers ont debarque. Merci a l'equipage pour ce vol, et {salut}."},
    "en": {"boarding_start": "Captain, boarding is starting.",
           "boarding_start_prevu": "Captain, boarding is starting. We are expecting {prevu} passengers.",
           "boarding_done_ok": "Captain, boarding is complete. We have {n} passengers on board, matching the flight plan.",
           "boarding_done_diff": "Captain, boarding is complete. We have {n} passengers on board, against {prevu} planned.",
           "boarding_done_nosb": "Captain, boarding is complete. We have {n} passengers on board.",
           "deboarding_start": "Captain, deboarding is starting.",
           "deboarding_done": "Captain, all passengers have deboarded. Thank you to the crew for this flight, and {salut}."},
    "de": {"boarding_start": "Kapitaen, das Boarding beginnt.",
           "boarding_start_prevu": "Kapitaen, das Boarding beginnt. Wir erwarten {prevu} Passagiere.",
           "boarding_done_ok": "Kapitaen, das Boarding ist abgeschlossen. Wir haben {n} Passagiere an Bord, wie im Flugplan vorgesehen.",
           "boarding_done_diff": "Kapitaen, das Boarding ist abgeschlossen. Wir haben {n} Passagiere an Bord, gegenueber {prevu} geplanten.",
           "boarding_done_nosb": "Kapitaen, das Boarding ist abgeschlossen. Wir haben {n} Passagiere an Bord.",
           "deboarding_start": "Kapitaen, das Aussteigen beginnt.",
           "deboarding_done": "Kapitaen, alle Passagiere haben das Flugzeug verlassen. Danke an die Crew fuer diesen Flug, und {salut}."},
    "es": {"boarding_start": "Comandante, el embarque comienza.",
           "boarding_start_prevu": "Comandante, el embarque comienza. Esperamos {prevu} pasajeros.",
           "boarding_done_ok": "Comandante, el embarque ha finalizado. Tenemos {n} pasajeros a bordo, conforme al plan de vuelo.",
           "boarding_done_diff": "Comandante, el embarque ha finalizado. Tenemos {n} pasajeros a bordo, frente a {prevu} previstos.",
           "boarding_done_nosb": "Comandante, el embarque ha finalizado. Tenemos {n} pasajeros a bordo.",
           "deboarding_start": "Comandante, el desembarque comienza.",
           "deboarding_done": "Comandante, todos los pasajeros han desembarcado. Gracias a la tripulacion por este vuelo, y {salut}."},
}


def _pax_prevu_simbrief():
    """Nombre de passagers prevus d'apres le dernier plan SimBrief charge, ou None si indisponible."""
    try:
        plan = lire_plan()
        w = plan.get("weights", {}) or {}
        for cle in ("pax_count", "pax_count_actual"):
            if w.get(cle):
                return int(w[cle])
        g = plan.get("general", {}) or {}
        if g.get("passengers"):
            return int(g["passengers"])
    except Exception:
        pass
    return None


_PROFIL_COMMANDANT_CACHE = []


def _profil_commandant():
    """Renvoie TOUJOURS le meme profil de voix pour les messages en direct au
    commandant (embarquement/debarquement GSX) : celui deja choisi pour ce vol
    lors de la generation du pack (etat.json, cle 'voix_chef_cabine'), afin que
    ce soit le meme chef de cabine qui parle aux passagers et au commandant,
    du debut a la fin du vol. Mis en cache apres le premier appel (un seul
    processus --auto-msfs tourne par vol)."""
    if not _PROFIL_COMMANDANT_CACHE:
        nom_voix = lit_etat().get("voix_chef_cabine")
        prof = next((p for p in PROFILS if p[0] == nom_voix), None) or random.choice(PROFILS)
        _PROFIL_COMMANDANT_CACHE.append(prof)
    return _PROFIL_COMMANDANT_CACHE[0]


async def _parler_commandant(cle, **kwargs):
    """Synthese vocale + lecture immediate sur les haut-parleurs de l'ordinateur
    (contrairement aux annonces cabine : pas de fichier pre-genere declenche par
    MSFS, car le nombre de passagers est variable d'un vol a l'autre)."""
    try:
        texte = ANNONCES_GSX.get(LANG, ANNONCES_GSX["en"])[cle].format(**kwargs)
        prof = _profil_commandant()
        v_prim = prof[0]
        debit, haut = prof[2], prof[3]
        tmp = os.path.join(WORK, "tmp_gsx")
        os.makedirs(tmp, exist_ok=True)
        base = os.path.join(tmp, "gsx_%d" % int(time.time() * 1000))
        mp3, wav = base + ".mp3", base + ".wav"
        ok = await tts(texte, v_prim, debit, haut, mp3, asyncio.Semaphore(1))
        if ok:
            try:
                ffmpeg("-i", mp3, wav)
                import winsound
                winsound.PlaySound(wav, winsound.SND_FILENAME)
            except Exception as e:
                print("[GSX] lecture audio impossible : %r" % e)
        for f in (mp3, wav):
            try:
                os.remove(f)
            except Exception:
                pass
    except Exception as e:
        print("[GSX] erreur annonce commandant (%s) : %r" % (cle, e))


def surveillance_gsx(arreter=None):
    """Boucle de surveillance des LVars GSX Pro (embarquement/debarquement) via
    le pont MobiFlight (module mobiflight-event-module, deja installe dans la
    Communaute). Informe le commandant en direct par synthese vocale :
    - debut d'embarquement
    - fin d'embarquement, avec confirmation du nombre de passagers a bord
      (compare au plan SimBrief si disponible)
    - debut de debarquement
    - fin de debarquement (tout le monde a debarque)
    Tourne en parallele de surveillance_simconnect, dans son propre thread."""
    try:
        from simconnect_mobiflight import SimConnectMobiFlight
        from mobiflight_variable_requests import MobiFlightVariableRequests
    except ImportError:
        print("[GSX] simconnect_mobiflight.py / mobiflight_variable_requests.py absents : "
              "annonces commandant GSX desactivees.")
        return

    V_BOARD_PAX = "(L:FSDT_GSX_NUMPASSENGERS_BOARDING)"
    V_DEBOARD_PAX = "(L:FSDT_GSX_NUMPASSENGERS_DEBOARDING)"
    SEUIL_STABLE = 12  # ~24s sans changement (boucle de 2s) = embarquement/debarquement considere termine

    vr = None
    pax_prevu = None
    embarquement_en_cours = embarquement_annonce_fin = False
    debarquement_en_cours = debarquement_annonce_fin = False
    dernier_pax_board = dernier_pax_deboard = 0
    stable_depuis_board = stable_depuis_deboard = 0

    while arreter is None or not arreter.is_set():
        try:
            if vr is None:
                try:
                    sm = SimConnectMobiFlight()
                    vr = MobiFlightVariableRequests(sm)
                    vr.clear_sim_variables()
                    print("[GSX] connecte (pont MobiFlight).")
                    pax_prevu = None
                    embarquement_en_cours = embarquement_annonce_fin = False
                    debarquement_en_cours = debarquement_annonce_fin = False
                    dernier_pax_board = dernier_pax_deboard = 0
                    stable_depuis_board = stable_depuis_deboard = 0
                except Exception:
                    vr = None
                    _attendre(15, arreter)
                    continue

            v_board = vr.get(V_BOARD_PAX)
            v_deboard = vr.get(V_DEBOARD_PAX)
            pax_board = int(v_board) if v_board is not None else 0
            pax_deboard = int(v_deboard) if v_deboard is not None else 0

            if pax_board > 0 and not embarquement_en_cours:
                embarquement_en_cours = True
                embarquement_annonce_fin = False
                stable_depuis_board = 0
                if pax_prevu is None:
                    pax_prevu = _pax_prevu_simbrief()
                print("[GSX] embarquement detecte.")
                if pax_prevu:
                    asyncio.run(_parler_commandant("boarding_start_prevu", prevu=pax_prevu))
                else:
                    asyncio.run(_parler_commandant("boarding_start"))
            if embarquement_en_cours and not embarquement_annonce_fin:
                if pax_board == dernier_pax_board and pax_board > 0:
                    stable_depuis_board += 1
                else:
                    stable_depuis_board = 0
                if stable_depuis_board >= SEUIL_STABLE:
                    embarquement_annonce_fin = True
                    print("[GSX] embarquement termine : %d passagers." % pax_board)
                    if pax_prevu and pax_prevu != pax_board:
                        asyncio.run(_parler_commandant("boarding_done_diff", n=pax_board, prevu=pax_prevu))
                    elif pax_prevu:
                        asyncio.run(_parler_commandant("boarding_done_ok", n=pax_board))
                    else:
                        asyncio.run(_parler_commandant("boarding_done_nosb", n=pax_board))

            if pax_deboard > 0 and not debarquement_en_cours:
                debarquement_en_cours = True
                debarquement_annonce_fin = False
                stable_depuis_deboard = 0
                print("[GSX] debarquement detecte.")
                asyncio.run(_parler_commandant("deboarding_start"))
            if debarquement_en_cours and not debarquement_annonce_fin:
                if pax_deboard == dernier_pax_deboard and pax_deboard > 0:
                    stable_depuis_deboard += 1
                else:
                    stable_depuis_deboard = 0
                cible = pax_board or pax_prevu
                termine_par_cible = bool(cible) and pax_deboard >= cible
                if stable_depuis_deboard >= SEUIL_STABLE or termine_par_cible:
                    debarquement_annonce_fin = True
                    print("[GSX] debarquement termine : %d passagers." % pax_deboard)
                    asyncio.run(_parler_commandant("deboarding_done", salut=salut_fin_service_par_langue().get(LANG, "")))

            dernier_pax_board, dernier_pax_deboard = pax_board, pax_deboard
            _attendre(2, arreter)
        except Exception as e:
            print("[GSX] erreur boucle (on reessaie dans 15s) : %r" % e)
            vr = None
            _attendre(15, arreter)


def boucle_auto_msfs():
    """Lance par MSFS lui-meme (EXE.xml, --auto-msfs) : surveille les vols
    via SimConnect comme surveillance_simconnect, et se ferme tout seul des
    que MSFS 2024 n'est plus en cours d'execution."""
    print("=" * 70)
    print("%s - connexion automatique (lance par MSFS)" % NOM_PRODUIT)
    print("=" * 70)
    arreter = threading.Event()

    def _surveiller_fermeture_msfs():
        time.sleep(20)  # laisse le temps a MSFS de finir de demarrer
        while not arreter.is_set():
            if not _msfs_tourne():
                print("MSFS 2024 ferme : arret automatique du programme.")
                arreter.set()
                return
            time.sleep(10)

    threading.Thread(target=_surveiller_fermeture_msfs, daemon=True).start()
    _demarre_serveur_config_toolbar(arreter)
    # annonces au commandant (debut/fin embarquement et debarquement, en direct via GSX) :
    # tourne dans son propre thread, en parallele de la boucle de generation ci-dessous.
    threading.Thread(target=surveillance_gsx, kwargs={"arreter": arreter}, daemon=True).start()
    surveillance_simconnect(arreter=arreter)


def creer_raccourci_bureau_si_absent():
    """Cree un raccourci bureau vers l'exe (avec son icone) au premier lancement,
    pour que l'utilisateur puisse rouvrir cette fenetre de parametres (SimBrief,
    dossier Community, langue, relancer l'installation) sans repasser par le
    dossier d'installation. La compagnie n'est plus selectionnee ici : elle est
    reconnue automatiquement en vol. Ne fait rien en mode developpement (python
    eurowings_cabin_v3.py), seulement sur l'exe empaquete. Jamais bloquant :
    une erreur ici est ignoree."""
    if not getattr(sys, "frozen", False):
        return
    try:
        bureau = os.path.join(os.path.expanduser("~"), "Desktop")
        lien = os.path.join(bureau, NOM_RACCOURCI)
        # migration : un raccourci cree sous un nom de produit precedent est
        # remplace par le nouveau (sinon les deux coexisteraient sur le Bureau).
        for ancien in NOMS_RACCOURCI_ANCIENS:
            _supprimer_si_existe(os.path.join(bureau, ancien))
        if os.path.isfile(lien):
            return
        cible = sys.executable
        ps = (
            "$s = New-Object -ComObject WScript.Shell; "
            "$sc = $s.CreateShortcut('{lien}'); "
            "$sc.TargetPath = '{cible}'; "
            "$sc.WorkingDirectory = '{dossier}'; "
            "$sc.IconLocation = '{cible}'; "
            "$sc.Description = '%s - Cleardeck Studio'; "
            "$sc.Save()"
        ).format(lien=lien, cible=cible, dossier=os.path.dirname(cible)) % NOM_PRODUIT
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
            capture_output=True,
        )
    except Exception:
        pass


def desinscrire_exe_xml():
    """Inverse de inscrire_exe_xml() : retire l'entree d'auto-lancement de
    EXE.xml si elle existe, sans toucher a rien d'autre dans le fichier.
    Renvoie (True, info) si retiree ou deja absente, (False, raison) sinon.
    Jamais bloquant pour la desinstallation du reste."""
    chemin = _chemin_exe_xml()
    if not chemin or not os.path.isfile(chemin):
        return True, "EXE.xml introuvable (rien a retirer)."
    nom_addon = NOM_PRODUIT
    try:
        texte = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(chemin, encoding=enc) as f:
                    texte = f.read()
                break
            except Exception:
                texte = None
        if texte is None:
            return False, "EXE.xml illisible (encodage)."
        retire_au_moins_une = False
        try:
            shutil.copyfile(chemin, chemin + ".bak_avant_desinstall")
        except Exception:
            pass
        for nom in [nom_addon] + NOMS_PRODUIT_ANCIENS:
            debut = texte.find("<Name>%s</Name>" % nom)
            if debut == -1:
                continue
            a = texte.rfind("<Launch.Addon>", 0, debut)
            b = texte.find("</Launch.Addon>", debut)
            if a == -1 or b == -1:
                continue
            b += len("</Launch.Addon>")
            fin = b
            if texte[fin:fin + 1] == "\n":
                fin += 1
            texte = texte[:a] + texte[fin:]
            retire_au_moins_une = True
        if not retire_au_moins_une:
            return True, "Entree deja absente."
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(texte)
        return True, chemin
    except Exception as e:
        return False, repr(e)


def _supprimer_si_existe(chemin):
    """Supprime un fichier ou un dossier s'il existe ; ignore silencieusement
    toute erreur (fichier verrouille, deja absent, droits...)."""
    try:
        if os.path.isdir(chemin):
            shutil.rmtree(chemin, ignore_errors=True)
        elif os.path.isfile(chemin):
            os.remove(chemin)
    except Exception:
        pass


def lancer_auto_suppression_dossier(dossier):
    """Programme la suppression du dossier d'installation (HERE, avec l'exe
    lui-meme dedans) une fois ce programme ferme : un .exe Windows ne peut
    pas se supprimer lui-meme pendant qu'il tourne. Ecrit un petit script
    PowerShell dans un dossier temporaire (en dehors de 'dossier', donc il
    survit a la suppression) qui attend la fin de CE processus, reessaie
    plusieurs fois la suppression (le temps que l'antivirus/Explorer
    relache le fichier .exe), puis se supprime lui-meme ; le lance ensuite
    en processus detache (DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP :
    survit a la fermeture de ce programme, sans combiner cela avec
    CREATE_NO_WINDOW, combinaison qui peut faire silencieusement echouer
    le lancement sur certaines configurations). Renvoie True si le script
    a pu etre ecrit et lance, False sinon (la suppression du dossier
    reste alors a faire a la main, ce qui est indique au simmer)."""
    try:
        tmp = os.environ.get("TEMP") or os.environ.get("TMP") or os.path.expanduser("~")
        script = os.path.join(tmp, "eurowings_cabin_v3_desinstall_%d.ps1" % os.getpid())
        contenu = (
            "$ErrorActionPreference = 'SilentlyContinue'\r\n"
            "Wait-Process -Id %d\r\n"
            "Start-Sleep -Seconds 2\r\n"
            "for ($i = 0; $i -lt 10; $i++) {\r\n"
            "    try {\r\n"
            "        Remove-Item -LiteralPath '%s' -Recurse -Force -ErrorAction Stop\r\n"
            "        break\r\n"
            "    } catch {\r\n"
            "        Start-Sleep -Seconds 2\r\n"
            "    }\r\n"
            "}\r\n"
            "Remove-Item -LiteralPath '%s' -Force -ErrorAction SilentlyContinue\r\n"
        ) % (os.getpid(), dossier.replace("'", "''"), script.replace("'", "''"))
        with open(script, "w", encoding="utf-8") as f:
            f.write(contenu)
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", script],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def desinstaller_application(log=print):
    """Desinstallation complete et sans risque pour MSFS/Fenix : ne supprime
    que ce que CE programme a lui-meme cree (son entree EXE.xml, le pack
    audio genere, son raccourci bureau, son fichier de configuration, et
    enfin son propre dossier d'installation). Ne touche jamais aux livrees
    Fenix, aux autres add-ons, ni a rien d'autre dans le dossier Community."""
    try:
        ok, info = desinscrire_exe_xml()
        log("Connexion automatique MSFS retiree." if ok else "Connexion automatique MSFS : %s" % info)
    except Exception as e:
        log("Connexion automatique MSFS : %r" % e)

    if PKG and os.path.isdir(PKG):
        _supprimer_si_existe(PKG)
        log("Pack audio supprime (%s)." % PKG)
    else:
        log("Pack audio deja absent.")

    bureau = os.path.join(os.path.expanduser("~"), "Desktop")
    for nom_lien in [NOM_RACCOURCI] + NOMS_RACCOURCI_ANCIENS:
        _supprimer_si_existe(os.path.join(bureau, nom_lien))
    log("Raccourci bureau supprime.")

    _supprimer_si_existe(CONFIG_PATH)
    log("Fichier de configuration supprime.")

    if getattr(sys, "frozen", False):
        if lancer_auto_suppression_dossier(HERE):
            log("Le dossier d'installation du programme sera supprime automatiquement a sa fermeture.")
        else:
            log("Le dossier d'installation n'a pas pu etre programme pour suppression automatique ; "
                "vous pouvez le supprimer vous-meme : %s" % HERE)
    else:
        log("Mode developpement : le dossier du script n'est pas supprime automatiquement.")


def lancer_gui():
    """Fenetre graphique affichee quand l'executable est lance sans argument
    (double-clic). Un seul bouton 'Installation' : configure, genere le pack,
    inscrit l'auto-lancement avec MSFS (EXE.xml), puis se ferme toute seule.
    Les vols suivants : le programme se relance et se ferme tout seul avec
    MSFS (voir --auto-msfs / boucle_auto_msfs), sans rien a faire.
    Un raccourci bureau est cree au premier lancement (voir
    creer_raccourci_bureau_si_absent) pour pouvoir rouvrir cette fenetre
    (SimBrief, dossier Community, langue, relancer l'installation)
    facilement plus tard."""
    creer_raccourci_bureau_si_absent()
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext

    fen = tk.Tk()
    fen.title("%s - v%s" % (NOM_PRODUIT, VERSION))
    fen.geometry("780x640")
    fen.minsize(620, 520)

    try:
        chemin_icone = _recurso("avatar_cleardeck.png")
        if os.path.isfile(chemin_icone):
            img_icone = tk.PhotoImage(file=chemin_icone)
            fen.iconphoto(True, img_icone)
            fen._icone_ref = img_icone  # garder une reference (sinon le ramasse-miettes la supprime)
    except Exception:
        pass

    # Bandeau logo : l'icone de barre de titre est imposee et minuscule par
    # Windows, donc on affiche en plus le logo en grand dans la fenetre.
    bandeau = tk.Frame(fen, bg="#10131a")
    bandeau.pack(fill="x", side="top")
    try:
        chemin_logo = _recurso("avatar_cleardeck.png")
        if os.path.isfile(chemin_logo):
            img_logo_brut = tk.PhotoImage(file=chemin_logo)
            img_logo = img_logo_brut.subsample(4, 4)  # 512px -> 128px
            lbl_logo = tk.Label(bandeau, image=img_logo, bg="#10131a")
            lbl_logo._img_ref = img_logo
            lbl_logo.pack(side="left", padx=14, pady=10)
    except Exception:
        pass
    cadre_titre = tk.Frame(bandeau, bg="#10131a")
    cadre_titre.pack(side="left", padx=(0, 14))
    tk.Label(cadre_titre, text=NOM_PRODUIT, fg="#ffffff", bg="#10131a",
             font=("Segoe UI", 15, "bold")).pack(anchor="w")
    tk.Label(cadre_titre, text="Cleardeck Studio - v%s" % VERSION, fg="#f2b705", bg="#10131a",
             font=("Segoe UI", 10)).pack(anchor="w")

    notebook = ttk.Notebook(fen)
    notebook.pack(fill="both", expand=True)
    onglet_install = ttk.Frame(notebook)
    onglet_desinstall = ttk.Frame(notebook)
    notebook.add(onglet_install, text="Installation")
    notebook.add(onglet_desinstall, text="Desinstaller / Uninstall")

    cadre = ttk.Frame(onglet_install, padding=14)
    cadre.pack(fill="both", expand=True)
    cadre.columnconfigure(1, weight=1)

    ttk.Label(cadre, text="Identifiant SimBrief / SimBrief Pilot ID").grid(row=0, column=0, sticky="w", pady=6)
    v_id = tk.StringVar(value=SIMBRIEF_ID)
    ttk.Entry(cadre, textvariable=v_id).grid(row=0, column=1, columnspan=2, sticky="we", pady=6)

    ttk.Label(cadre, text="Dossier Community MSFS 2024 / MSFS 2024 Community folder").grid(row=1, column=0, sticky="w", pady=6)
    comm_defaut = COMMUNITY or next((c for c in _candidats_community() if os.path.isdir(c)), "")
    v_comm = tk.StringVar(value=comm_defaut)
    ttk.Entry(cadre, textvariable=v_comm).grid(row=1, column=1, sticky="we", pady=6)

    def parcourir():
        d = filedialog.askdirectory(title="Choisissez le dossier Community / Choose the Community folder",
                                     initialdir=v_comm.get() or os.path.expanduser("~"))
        if d:
            v_comm.set(d)
    ttk.Button(cadre, text="Parcourir... / Browse...", command=parcourir).grid(row=1, column=2, padx=(6, 0), pady=6)

    ttk.Label(cadre, text="Langue des annonces / Announcement language").grid(row=2, column=0, sticky="w", pady=6)
    cles = list(LANGUES.keys())
    cle_defaut = next((k for k in cles if LANGUES[k][0] == LANG), cles[0])
    libelles_langue = {k: "%s / %s" % (LANGUES[k][1], LANGUES[k][2]) for k in cles}
    v_langue = tk.StringVar(value=libelles_langue[cle_defaut])
    cb = ttk.Combobox(cadre, textvariable=v_langue, values=list(libelles_langue.values()), state="readonly")
    cb.grid(row=2, column=1, columnspan=2, sticky="we", pady=6)

    # La compagnie n'a plus de champ ici : elle est reconnue automatiquement
    # en vol via la livree active (voir livree_active_via_simconnect).

    deja_installe = bool(_charge_config().get("simbrief_id"))
    bouton = ttk.Button(cadre, text="Mettre a jour / Update" if deja_installe else "Installation / Install")
    bouton.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="we")

    journal = scrolledtext.ScrolledText(cadre, height=12, state="disabled", wrap="word")
    journal.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(14, 0))
    cadre.rowconfigure(8, weight=1)

    dernier_est_progres = [False]

    def log(texte):
        est_progres = texte.startswith("Progression :")
        def _ajoute():
            journal.config(state="normal")
            if est_progres and dernier_est_progres[0]:
                try:
                    journal.delete("end-2l", "end-1l")
                except Exception:
                    pass
            journal.insert("end", texte + "\n")
            journal.see("end")
            journal.config(state="disabled")
            dernier_est_progres[0] = est_progres
        fen.after(0, _ajoute)

    class _FluxLog:
        def __init__(self):
            self.echecs_voix = 0
            self._tampon = ""
        def write(self, s):
            self._tampon += s
            while "\n" in self._tampon:
                ligne, self._tampon = self._tampon.split("\n", 1)
                self._traiter(ligne)
        def _traiter(self, ligne):
            texte = ligne.rstrip()
            if not texte.strip():
                return
            if ("ECHEC voix" in texte or "ECHEC clip" in texte
                    or "exception inattendue" in texte):
                self.echecs_voix += 1
                return  # pas affiche : message confus pour l'utilisateur
            if texte.startswith("Vol ") and "->" in texte:
                return  # aeroports/plan SimBrief : pas affiche dans la fenetre
            log(texte)
        def flush(self):
            pass

    def lancer():
        pid = v_id.get().strip()
        dossier = v_comm.get().strip().strip('"')
        if not pid.isdigit():
            messagebox.showerror("Identifiant invalide / Invalid ID",
                                  "L'identifiant SimBrief doit etre un nombre (Pilot ID, sur simbrief.com > Account).\n\n"
                                  "The SimBrief ID must be a number (your Pilot ID, on simbrief.com > Account).")
            return
        if not os.path.isdir(dossier):
            messagebox.showerror("Dossier introuvable / Folder not found",
                                  "Le dossier Community indique n'existe pas.\n\nThe Community folder given does not exist.")
            return
        libelle_choisi = v_langue.get()
        cle_choisie = next((k for k in cles if libelles_langue[k] == libelle_choisi), cle_defaut)

        global SIMBRIEF_ID, COMMUNITY, NOM_EQUIPAGE, LANG, PKG, COMPAGNIE, CODES

        # La compagnie/code ICAO ne sont plus choisis ici : ils sont reconnus
        # automatiquement en vol (livree_active_via_simconnect, dans
        # surveillance_simconnect) a partir de l'immatriculation de la livree
        # active. On garde ici la derniere valeur connue (par defaut
        # "Eurowings" au tout premier lancement) uniquement comme repli tant
        # qu'aucun vol n'a encore ete detecte.
        SIMBRIEF_ID = pid
        COMMUNITY = dossier
        LANG = LANGUES[cle_choisie][0]
        NOM_EQUIPAGE = prenom_chef_cabine_aleatoire(LANG)
        PKG = os.path.join(COMMUNITY, "fnx-cabin-announcements-cleardeck")
        _sauve_config({"simbrief_id": SIMBRIEF_ID, "community": COMMUNITY, "langue": LANG, "nom_equipage": NOM_EQUIPAGE,
                        "compagnie": COMPAGNIE, "codes_compagnie": ",".join(CODES)})

        bouton.config(state="disabled", text="Installation en cours... / Installing...")
        journal.config(state="normal"); journal.delete("1.0", "end"); journal.config(state="disabled")

        def travail():
            ancien_stdout = sys.stdout
            flux = _FluxLog()
            sys.stdout = flux
            erreur = None
            try:
                executer(["--tout"])
            except Exception as e:
                erreur = e
            finally:
                sys.stdout = ancien_stdout

            auto_ok, auto_info = (False, None)
            if erreur is None:
                try:
                    auto_ok, auto_info = inscrire_exe_xml()
                    if auto_ok:
                        log("Connexion automatique MSFS activee (%s)." % auto_info)
                    else:
                        log("Connexion automatique MSFS non activee : %s" % auto_info)
                except Exception as e:
                    auto_ok, auto_info = False, repr(e)
                    log("Connexion automatique MSFS non activee : %r" % e)

                try:
                    resultat_mf = installer_module_mobiflight_si_necessaire(COMMUNITY, log=log)
                    if resultat_mf == "gsx_absent":
                        log("GSX Pro non detecte : annonces en direct au commandant desactivees (pas bloquant).")
                    elif resultat_mf == "deja_present":
                        log("GSX detecte, pont MobiFlight deja present : annonces en direct au commandant activees.")
                    elif resultat_mf == "installe":
                        log("GSX detecte : pont MobiFlight installe automatiquement, annonces en direct au commandant activees.")
                except Exception as e:
                    log("Pont MobiFlight (GSX) : installation automatique impossible : %r" % e)

            def fin():
                if erreur:
                    bouton.config(state="normal",
                                  text="Mettre a jour / Update" if deja_installe else "Installation / Install")
                    messagebox.showerror(
                        "Erreur / Error",
                        "L'installation a echoue :\n%r\n\nThe installation failed:\n%r" % (erreur, erreur))
                    return
                if flux.echecs_voix:
                    messagebox.showwarning(
                        "Installation reussie (partiellement) / Installation successful (partially)",
                        "Installation reussie, mais %d annonce(s) n'ont pas pu etre generees (probleme reseau "
                        "passager) : ce n'est pas bloquant, le pack fonctionne quand meme.\n\n"
                        "Installation successful, but %d announcement(s) could not be generated (temporary "
                        "network issue): this is not blocking, the pack still works." % (flux.echecs_voix, flux.echecs_voix))
                else:
                    messagebox.showinfo(
                        "Installation reussie / Installation successful",
                        "Installation reussie. Lancez MSFS 2024 quand vous voulez : l'outil se connectera\n"
                        "automatiquement et se fermera avec MSFS, sans rien a faire.\n\n"
                        "Installation successful. Start MSFS 2024 whenever you like: the tool will connect\n"
                        "automatically and close together with MSFS, nothing else to do.")
                fen.destroy()
            fen.after(0, fin)

        threading.Thread(target=travail, daemon=True).start()

    bouton.config(command=lancer)

    # --- onglet Desinstaller / Uninstall ---
    cadre_u = ttk.Frame(onglet_desinstall, padding=14)
    cadre_u.pack(fill="both", expand=True)
    cadre_u.columnconfigure(0, weight=1)

    ttk.Label(
        cadre_u,
        text="Desinstaller l'application / Uninstall the application",
        font=("TkDefaultFont", 11, "bold"),
    ).grid(row=0, column=0, sticky="w", pady=(0, 8))

    ttk.Label(
        cadre_u,
        justify="left",
        wraplength=680,
        text=(
            "Cette action supprime uniquement ce que ce programme a lui-meme cree, sans jamais toucher "
            "a MSFS, a Fenix, a vos livrees ou a vos autres add-ons :\n"
            "  - le pack audio genere dans le dossier Community (fnx-cabin-announcements-cleardeck)\n"
            "  - la connexion automatique avec MSFS (entree EXE.xml)\n"
            "  - le raccourci sur le Bureau\n"
            "  - le fichier de configuration\n"
            "  - le dossier et le programme lui-meme (apres sa fermeture)\n\n"
            "This only removes what this program itself created, and never touches MSFS, Fenix, your "
            "liveries or other add-ons:\n"
            "  - the generated audio pack in the Community folder (fnx-cabin-announcements-cleardeck)\n"
            "  - the automatic connection with MSFS (EXE.xml entry)\n"
            "  - the Desktop shortcut\n"
            "  - the configuration file\n"
            "  - the program's own folder (once it closes)\n\n"
            "Cette action est irreversible / This action cannot be undone."
        ),
    ).grid(row=1, column=0, sticky="w", pady=(0, 14))

    bouton_u = ttk.Button(cadre_u, text="Desinstaller / Uninstall")
    bouton_u.grid(row=2, column=0, sticky="w")

    journal_u = scrolledtext.ScrolledText(cadre_u, height=10, state="disabled", wrap="word")
    journal_u.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
    cadre_u.rowconfigure(3, weight=1)

    def log_u(texte):
        def _ajoute():
            journal_u.config(state="normal")
            journal_u.insert("end", str(texte) + "\n")
            journal_u.see("end")
            journal_u.config(state="disabled")
        fen.after(0, _ajoute)

    def desinstaller():
        confirme = messagebox.askyesno(
            "Confirmer la desinstallation / Confirm uninstall",
            "Etes-vous sur de vouloir desinstaller l'application ?\n\n"
            "Seront supprimes : le pack audio genere, le raccourci bureau, le fichier de configuration, "
            "la connexion automatique MSFS, et enfin le dossier du programme lui-meme.\n"
            "Vos livrees Fenix et le reste de votre dossier Community ne sont pas touches.\n\n"
            "Cette action est irreversible.\n\n"
            "Are you sure you want to uninstall the application?\n\n"
            "This will remove: the generated audio pack, the desktop shortcut, the configuration file, "
            "the automatic MSFS connection, and finally the program's own folder.\n"
            "Your Fenix liveries and the rest of your Community folder are left untouched.\n\n"
            "This action cannot be undone.",
            icon="warning",
            default="no",
        )
        if not confirme:
            return
        bouton_u.config(state="disabled", text="Desinstallation en cours... / Uninstalling...")
        journal_u.config(state="normal"); journal_u.delete("1.0", "end"); journal_u.config(state="disabled")

        def travail_u():
            try:
                desinstaller_application(log=log_u)
            except Exception as e:
                log_u("Erreur inattendue / Unexpected error: %r" % e)

            def fin_u():
                if getattr(sys, "frozen", False):
                    messagebox.showinfo(
                        "Desinstallation terminee / Uninstall complete",
                        "Desinstallation terminee. L'application va se fermer ; son dossier sera "
                        "supprime automatiquement dans quelques secondes.\n\n"
                        "Uninstall complete. The application will now close; its folder will be "
                        "removed automatically in a few seconds.")
                else:
                    messagebox.showinfo(
                        "Desinstallation terminee / Uninstall complete",
                        "Desinstallation terminee.\n\nUninstall complete.")
                fen.destroy()
            fen.after(0, fin_u)

        threading.Thread(target=travail_u, daemon=True).start()

    bouton_u.config(command=desinstaller)

    fen.mainloop()
def main():
    argv = sys.argv[1:]
    if not argv:
        lancer_gui()
        return
    if "--boucle" in argv:
        print("=" * 70)
        print("%s - mode boucle" % NOM_PRODUIT)
        print("Reste ouvert et verifie toutes les 2 minutes : nouveau plan SimBrief")
        print("ou meteo d'arrivee changee pendant que MSFS tourne.")
        print("Fermez cette fenetre pour arreter. Ctrl+C fonctionne aussi.")
        print("=" * 70)
        while True:
            try:
                executer(["--auto", "--meteo"])
            except KeyboardInterrupt:
                print("Arret demande."); return
            except Exception as ex:
                print("[Boucle] erreur (on reessaie dans 2 min) : %r" % ex)
            time.sleep(120)
    elif "--simconnect" in argv:
        surveillance_simconnect()
    elif "--auto-msfs" in argv:
        boucle_auto_msfs()
    else:
        executer(argv)
        input("\nAppuyez sur Entree pour fermer cette fenetre / Press Enter to close this window... ")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        trace = traceback.format_exc()
        try:
            with open(os.path.join(HERE, "erreur_demarrage.log"), "w", encoding="utf-8") as f:
                f.write(trace)
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            _r = tk.Tk(); _r.withdraw()
            messagebox.showerror("Erreur / Error", "Une erreur est survenue / An error occurred :\n\n%s" % trace)
        except Exception:
            pass