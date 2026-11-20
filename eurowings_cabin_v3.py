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
CODES = ["EWG", "EWL"]          # dossiers du pack cote Fenix (indicatif Eurowings + code compagnie)
NB_PARALLELE = 5
VERSION = "1.2.0"


def _candidats_community():
    appdata = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    return [
        os.path.join(local, "Packages", "Microsoft.Limitless_8wekyb3d8bbwe", "LocalCache", "Packages", "Community"),
        os.path.join(local, "Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "Packages", "Community"),
        os.path.join(appdata, "Microsoft Flight Simulator 2024", "Packages", "Community"),
        os.path.join(appdata, "Microsoft Flight Simulator", "Packages", "Community"),
    ]


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
        print("Eurowings Cabin Announcements V3 - Fenix A320 - premiere configuration")
        print("Eurowings Cabin Announcements V3 - Fenix A320 - first-time setup")
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


if len(sys.argv) > 1:
    _CFG = premiere_configuration()
else:
    _CFG = _charge_config()  # mode GUI (double-clic) : pas de prompts console, la fenetre s'en occupe
SIMBRIEF_ID = _CFG.get("simbrief_id", "")
COMMUNITY = _CFG.get("community", "")
NOM_EQUIPAGE = (_CFG.get("nom_equipage") or "").strip()
PKG = os.path.join(COMMUNITY, "fnx-airline-packs-eurowings") if COMMUNITY else ""
print("Eurowings Cabin Announcements V3 - version", VERSION)

# ------------------------------------------------------------------ voix
# (voix française, voix anglaise, débit, hauteur)
PROFILS_FR = [
    ("fr-FR-EloiseNeural", "en-GB-SoniaNeural", "+8%", "+0Hz"),
    ("fr-FR-DeniseNeural", "en-GB-SoniaNeural", "+6%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-GB-LibbyNeural", "+8%", "+0Hz"),
    ("fr-FR-DeniseNeural", "en-US-JennyNeural", "+6%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-US-AriaNeural", "+6%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-GB-SoniaNeural", "+10%", "+2Hz"),
    ("fr-FR-DeniseNeural", "en-GB-LibbyNeural", "+4%", "-2Hz"),
    ("fr-FR-DeniseNeural", "en-GB-LibbyNeural", "+6%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-GB-SoniaNeural", "+6%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-GB-SoniaNeural", "+10%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-US-AriaNeural", "+8%", "-2Hz"),
    ("fr-FR-DeniseNeural", "en-US-JennyNeural", "+8%", "+0Hz"),
    ("fr-FR-DeniseNeural", "en-GB-LibbyNeural", "+4%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-GB-SoniaNeural", "+8%", "+0Hz"),
    ("fr-FR-EloiseNeural", "en-US-AriaNeural", "+6%", "-2Hz"),
    ("fr-FR-EloiseNeural", "en-GB-LibbyNeural", "+12%", "+0Hz"),
    ("fr-FR-DeniseNeural", "en-US-AriaNeural", "+10%", "+2Hz"),
    ("fr-FR-DeniseNeural", "en-GB-SoniaNeural", "+10%", "+0Hz"),
    ("fr-FR-HenriNeural", "en-GB-RyanNeural", "+6%", "+0Hz"),
    ("fr-FR-HenriNeural", "en-GB-ThomasNeural", "+6%", "+0Hz"),
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
LANG = _CFG.get("langue", "fr")
SECONDE_LANGUE = None if LANG == "en" else "en"
PROFILS = PROFILS_PAR_LANGUE[LANG]

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
        hf = n_mot(h, L) + " " + (sing if h == 1 else plur)
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
    kt = m["kt"]
    if kt <= 6 or m["wd"] is None:
        return {"fr": "un vent faible", "en": "a light breeze", "de": "ein leichter Wind", "es": "un viento suave"}
    i = int(((m["wd"] % 360) + 22.5) // 45) % 8
    out = {}
    for L in LANGS:
        dirn = CARD[L][i]
        nk = n_mot(kt, L)
        if kt >= 25:
            out[L] = {"fr": "un vent soutenu de %s, %s nœuds" % (dirn, nk),
                       "en": "a strong %s wind, %s knots" % (dirn, nk),
                       "de": "kräftiger Wind aus %s, %s Knoten" % (dirn, nk),
                       "es": "viento fuerte del %s, %s nudos" % (dirn, nk)}[L]
        else:
            out[L] = {"fr": "un vent de %s de %s nœuds" % (dirn, nk),
                       "en": "a %s wind at %s knots" % (dirn, nk),
                       "de": "Wind aus %s mit %s Knoten" % (dirn, nk),
                       "es": "viento del %s de %s nudos" % (dirn, nk)}[L]
    return out


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
    EW = {"fr": "Eurowings", "en": "Eurowings", "de": "Eurowings", "es": "Eurowings"}
    nom = " (%s)" % NOM_EQUIPAGE if NOM_EQUIPAGE else ""

    # --- retard : compare l'heure estimee de depart a l'heure prevue ---
    retard_min = 0
    try:
        sched_out = int(tm.get("sched_out") or 0)
        est_out = int(tm.get("est_out") or sched_out)
        if sched_out:
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

    # --- repas : menu + boissons selon l'heure locale au depart ---
    try:
        tz_o = float(str(o.get("timezone") or 0))
    except Exception:
        tz_o = 0.0
    try:
        base_t = int(tm.get("est_out") or tm.get("sched_out") or 0)
    except Exception:
        base_t = 0
    heure_locale = time.gmtime(base_t + int(tz_o * 3600)).tm_hour if base_t else 12

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
    }
    BOISSONS = {"fr": "eau, jus de fruits, sodas, thé, café, et une sélection de vins et bières",
                "en": "water, fruit juice, soft drinks, tea, coffee, and a selection of wines and beers",
                "de": "Wasser, Fruchtsaft, Softdrinks, Tee, Kaffee sowie eine Auswahl an Wein und Bier",
                "es": "agua, zumo de frutas, refrescos, té, café, y una selección de vinos y cervezas"}

    if 23 <= heure_locale or heure_locale < 5:
        REPAS = {
            "fr": "Comme il s'agit d'un vol de nuit, le service sera léger : le nécessaire (eau, couvertures, collations) est à votre disposition aux emplacements prévus dans la cabine.",
            "en": "As this is a night flight, service will be light: water, blankets and snacks are available at the locations provided in the cabin.",
            "de": "Da es sich um einen Nachtflug handelt, fällt der Service schlicht aus: Wasser, Decken und Snacks finden Sie an den dafür vorgesehenen Stellen in der Kabine.",
            "es": "Al tratarse de un vuelo nocturno, el servicio será ligero: el agua, las mantas y los tentempiés están disponibles en los lugares previstos de la cabina.",
        }
    else:
        if 5 <= heure_locale < 10:
            cle, moment = "petit_dej", {"fr": "Comme il est tôt, nous vous proposons", "en": "As it is still early, we are offering you",
                                         "de": "Da es noch früh ist, bieten wir Ihnen", "es": "Como es temprano, les proponemos"}
        elif 10 <= heure_locale < 15:
            cle, moment = "dejeuner", {"fr": "Pour le déjeuner, nous vous proposons", "en": "For lunch, we are offering you",
                                        "de": "Zum Mittagessen bieten wir Ihnen", "es": "Para el almuerzo, les proponemos"}
        elif 15 <= heure_locale < 18:
            cle, moment = "collation", {"fr": "Nous vous proposons", "en": "We are offering you",
                                         "de": "Wir bieten Ihnen", "es": "Les proponemos"}
        else:
            cle, moment = "diner", {"fr": "Pour le dîner, nous vous proposons", "en": "For dinner, we are offering you",
                                     "de": "Zum Abendessen bieten wir Ihnen", "es": "Para la cena, les proponemos"}
        REPAS = {}
        for L in LANGS:
            menu_choisi = random.choice(MENUS[cle][L])
            REPAS[L] = "%s %s, accompagné%s de %s." % (moment[L], menu_choisi, "" if L != "fr" else "", BOISSONS[L])                 if L == "fr" else "%s %s, with %s." % (moment[L], menu_choisi, BOISSONS[L]) if L == "en"                 else "%s %s, dazu %s." % (moment[L], menu_choisi, BOISSONS[L]) if L == "de"                 else "%s %s, junto con %s." % (moment[L], menu_choisi, BOISSONS[L])

    # --- scenario rare (1 chance sur 10000) ---
    SCENARIO = {L: "" for L in LANGS}
    if random.random() < 1.0 / 10000:
        scenarios = [
            {"fr": " Avant de poursuivre, nous vous informons qu'une légère urgence médicale a été signalée à bord : si un médecin ou un professionnel de santé se trouve parmi vous, merci de bien vouloir se signaler à un membre de notre équipage.",
             "en": " Before we continue, we would like to inform you that a minor medical situation has been reported on board: if there is a doctor or a healthcare professional among you, please identify yourself to a crew member.",
             "de": " Bevor wir fortfahren, möchten wir Sie informieren, dass an Bord ein kleiner medizinischer Vorfall gemeldet wurde: Sollte sich ein Arzt oder eine medizinische Fachkraft unter Ihnen befinden, melden Sie sich bitte bei einem Besatzungsmitglied.",
             "es": " Antes de continuar, les informamos de que se ha notificado una leve emergencia médica a bordo: si hay un médico o profesional sanitario entre ustedes, identifíquese ante un miembro de la tripulación."},
            {"fr": " Nous profitons de ce moment pour vous informer qu'une de nos passagères est enceinte et approche du terme : si un médecin ou une sage-femme se trouve à bord, merci de bien vouloir se signaler discrètement à notre équipage.",
             "en": " We would also like to let you know that one of our passengers is expecting a baby and is close to her due date: if there is a doctor or a midwife on board, please discreetly identify yourself to our crew.",
             "de": " Wir möchten Sie zudem informieren, dass sich eine schwangere Passagierin kurz vor der Entbindung an Bord befindet: Sollte sich ein Arzt oder eine Hebamme unter Ihnen befinden, melden Sie sich bitte diskret bei unserer Besatzung.",
             "es": " Aprovechamos para informarles de que una de nuestras pasajeras está embarazada y próxima a dar a luz: si hay un médico o una matrona a bordo, identifíquese discretamente ante nuestra tripulación."},
            {"fr": " Nous venons d'être informés qu'un passager présente des signes de malaise cardiaque : nous demandons à tout médecin ou professionnel de santé présent à bord de bien vouloir se signaler immédiatement à notre équipage.",
             "en": " We have just been informed that a passenger is showing signs of a cardiac episode: we kindly ask any doctor or healthcare professional on board to identify themselves to our crew immediately.",
             "de": " Wir wurden soeben informiert, dass ein Fahrgast Anzeichen eines Herzproblems zeigt: Wir bitten jeden an Bord befindlichen Arzt oder jede medizinische Fachkraft, sich sofort bei unserer Besatzung zu melden.",
             "es": " Se nos acaba de informar de que un pasajero presenta síntomas de un episodio cardíaco: rogamos a cualquier médico o profesional sanitario a bordo que se identifique de inmediato ante nuestra tripulación."},
            {"fr": " Petite anecdote de ce vol : une personnalité connue du grand public voyage parmi nous aujourd'hui. Par discrétion, l'équipage ne dira rien de plus, mais gardez l'œil ouvert.",
             "en": " A small anecdote for this flight: a well-known public figure is travelling with us today. Out of discretion, the crew will say no more, but keep an eye out.",
             "de": " Eine kleine Anekdote für diesen Flug: Eine bekannte Persönlichkeit reist heute mit uns. Aus Diskretion sagt die Besatzung nicht mehr dazu, aber halten Sie die Augen offen.",
             "es": " Una pequeña anécdota de este vuelo: una conocida personalidad viaja hoy con nosotros. Por discreción, la tripulación no dirá nada más, pero estén atentos."},
        ]
        SCENARIO = random.choice(scenarios)

    out = {}
    for L in LANGS:
        out[L] = dict(EW=EW[L], FN=fn[L], ORIG=vo[L], DEST=vd[L], DUR=du[L], TEMP_O=to[L], TEMP_D=td[L],
                      SKY_O=so[L], SKY_D=sd[L], WIND_D=wd[L], COMMENT_D=cm[L], TURB=tu[L], NOM=nom,
                      RETARD=RETARD[L], REPAS=REPAS[L], SCENARIO=SCENARIO[L])
    return out


# ------------------------------------------------------------------ textes : (type, avec_carillon, personnalisé, [(fr, en), ...])
T = []


def add(nom, carillon, perso, variantes):
    T.append((nom, carillon, perso, variantes))


add("BoardingWelcome", True, True, [
    {"fr": "Mesdames et messieurs, bienvenue à bord de ce vol {EW} {FN}, à destination de {DEST}. Ici votre chef de cabine{NOM}.{RETARD} Installez-vous, et rangez vos bagages à main dans les coffres au-dessus de vos sièges, ou sous le siège devant vous. Si votre coffre est plein, c'est que quelqu'un a apporté tout son salon. Nous allons trouver une solution ensemble. Merci de votre patience.",
     "en": "Ladies and gentlemen, welcome aboard {EW} flight {FN} to {DEST}. This is your cabin manager{NOM} speaking.{RETARD} Please make yourselves comfortable, and stow your hand luggage in the overhead lockers, or under the seat in front of you. If your locker is full, someone brought their entire living room. We will find a solution together. Thank you for your patience.",
     "de": "Meine Damen und Herren, willkommen an Bord von {EW} Flug {FN} nach {DEST}. Hier spricht Ihr Kabinenchef{NOM}.{RETARD} Machen Sie es sich bequem und verstauen Sie Ihr Handgepäck in den Gepäckfächern über Ihrem Sitz oder unter dem Sitz vor Ihnen. Wenn Ihr Gepäckfach voll ist, hat wohl jemand sein ganzes Wohnzimmer mitgebracht. Wir finden gemeinsam eine Lösung. Vielen Dank für Ihre Geduld.",
     "es": "Señoras y señores, bienvenidos a bordo del vuelo {EW} {FN} con destino a {DEST}. Les habla su jefe de cabina{NOM}.{RETARD} Pónganse cómodos y guarden su equipaje de mano en los compartimentos superiores, o bajo el asiento delantero. Si su compartimento está lleno, es que alguien ha traído todo su salón. Encontraremos una solución juntos. Gracias por su paciencia."},
    {"fr": "Bienvenue à bord, mesdames et messieurs. Votre équipage vous souhaite un excellent vol {EW} à destination de {DEST}. Le temps de vol sera d'environ {DUR}. À {ORIG}, il fait actuellement {TEMP_O}, {SKY_O}. Prenez place, rangez vos affaires, et si vous avez le siège du milieu, toute notre compassion vous est acquise. Merci.",
     "en": "Welcome aboard, ladies and gentlemen. Your crew wishes you an excellent {EW} flight to {DEST}. Our flight time will be about {DUR}. In {ORIG}, it is currently {TEMP_O}, {SKY_O}. Please take your seats, stow your belongings, and if you have the middle seat, you have our full sympathy. Thank you.",
     "de": "Willkommen an Bord, meine Damen und Herren. Ihre Crew wünscht Ihnen einen angenehmen {EW}-Flug nach {DEST}. Die Flugzeit beträgt etwa {DUR}. In {ORIG} ist es derzeit {TEMP_O}, {SKY_O}. Nehmen Sie Platz, verstauen Sie Ihre Sachen, und wenn Sie den Mittelsitz haben, haben Sie unser volles Mitgefühl. Vielen Dank.",
     "es": "Bienvenidos a bordo, señoras y señores. Su tripulación les desea un excelente vuelo {EW} con destino a {DEST}. El tiempo de vuelo será de aproximadamente {DUR}. En {ORIG} hace actualmente {TEMP_O}, {SKY_O}. Tomen asiento, guarden sus pertenencias, y si tienen el asiento del medio, cuentan con toda nuestra compasión. Gracias."},
    {"fr": "Mesdames et messieurs, l'équipage de ce vol {EW} {FN} est heureux de vous accueillir à bord. Nous nous rendons à {DEST}. Pendant que vous vous installez, merci de ranger vos bagages, et de laisser les allées libres. Nous savons que le coffre de la rangée dix est très attirant, mais il y a de la place pour tout le monde. Merci.",
     "en": "Ladies and gentlemen, the crew of {EW} flight {FN} is delighted to welcome you on board. We are heading to {DEST}. While you settle in, please stow your bags, and keep the aisle clear. We know the locker above row ten looks very tempting, but there is room for everybody. Thank you.",
     "de": "Meine Damen und Herren, die Crew von {EW} Flug {FN} freut sich, Sie an Bord willkommen zu heißen. Unser Ziel ist {DEST}. Während Sie sich einrichten, verstauen Sie bitte Ihr Gepäck und halten Sie den Gang frei. Wir wissen, dass das Gepäckfach in Reihe zehn sehr verlockend ist, aber es ist für alle genug Platz. Vielen Dank.",
     "es": "Señoras y señores, la tripulación del vuelo {EW} {FN} se complace en darles la bienvenida a bordo. Nos dirigimos a {DEST}. Mientras se instalan, les rogamos guardar su equipaje y dejar el pasillo libre. Sabemos que el compartimento de la fila diez resulta muy tentador, pero hay sitio para todos. Gracias."},
])
add("BoardingComplete", True, True, [
    {"fr": "Mesdames et messieurs, l'embarquement est terminé. Merci d'avoir été aussi ponctuels. Nous allons bientôt fermer les portes. Votre temps de vol jusqu'à {DEST} sera d'environ {DUR}. Passez vos appareils électroniques en mode avion. Oui, même celui-là.",
     "en": "Ladies and gentlemen, boarding is now complete. Thank you for being so punctual. We will close the doors shortly. Your flight time to {DEST} will be about {DUR}. Please switch your electronic devices to flight mode. Yes, even that one.",
     "de": "Meine Damen und Herren, das Boarding ist abgeschlossen. Vielen Dank, dass Sie so pünktlich waren. Wir werden die Türen in Kürze schließen. Ihre Flugzeit nach {DEST} beträgt etwa {DUR}. Bitte schalten Sie Ihre elektronischen Geräte in den Flugmodus. Ja, auch dieses.",
     "es": "Señoras y señores, el embarque ha finalizado. Gracias por ser tan puntuales. En breve cerraremos las puertas. Su tiempo de vuelo hasta {DEST} será de aproximadamente {DUR}. Pongan sus dispositivos electrónicos en modo avión. Sí, incluso ese."},
    {"fr": "Mesdames et messieurs, tout le monde est à bord, c'est parfait. Les portes vont être fermées. Nous volerons vers {DEST} pendant environ {DUR}. Veuillez attacher votre ceinture, et mettre vos téléphones en mode avion. Merci.",
     "en": "Ladies and gentlemen, everybody is on board, which is perfect. The doors will now be closed. We will be flying to {DEST} for about {DUR}. Please fasten your seat belt, and put your phones in flight mode. Thank you.",
     "de": "Meine Damen und Herren, alle sind an Bord, perfekt. Die Türen werden nun geschlossen. Wir fliegen etwa {DUR} nach {DEST}. Bitte schließen Sie Ihren Sicherheitsgurt und schalten Sie Ihre Telefone in den Flugmodus. Vielen Dank.",
     "es": "Señoras y señores, todo el mundo está a bordo, perfecto. Las puertas van a cerrarse. Volaremos hacia {DEST} durante aproximadamente {DUR}. Abróchense el cinturón de seguridad y pongan sus teléfonos en modo avión. Gracias."},
    {"fr": "Mesdames et messieurs, l'embarquement est maintenant terminé. L'équipage vous remercie, et vous souhaite un excellent vol {EW} jusqu'à {DEST}. Merci de rester assis, de relever votre tablette, et de préparer votre meilleur sourire pour la démonstration de sécurité.",
     "en": "Ladies and gentlemen, boarding is now complete. The crew thanks you, and wishes you an excellent {EW} flight to {DEST}. Please remain seated, stow your tray table, and prepare your best smile for the safety demonstration.",
     "de": "Meine Damen und Herren, das Boarding ist nun abgeschlossen. Die Crew bedankt sich und wünscht Ihnen einen ausgezeichneten {EW}-Flug nach {DEST}. Bitte bleiben Sie sitzen, klappen Sie Ihren Tisch hoch, und halten Sie Ihr schönstes Lächeln für die Sicherheitsvorführung bereit.",
     "es": "Señoras y señores, el embarque ha finalizado. La tripulación les agradece y les desea un excelente vuelo {EW} hasta {DEST}. Permanezcan sentados, suban su mesita, y preparen su mejor sonrisa para la demostración de seguridad."},
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
    {"fr": "Il y a quatre sorties de secours, deux à l'avant, deux à l'arrière. Elles sont signalées par des bandes lumineuses au sol. Rassurez-vous, l'avion est symétrique. La ceinture : on l'attache en insérant la languette dans la boucle, et on la détache en ouvrant la boucle. Oui, c'est exactement comme dans une voiture. En cas de dépressurisation, des masques tomberont automatiquement. Tirez sur un masque, placez-le sur le nez et la bouche, et respirez normalement. Si vous voyagez avec un enfant, mettez d'abord le vôtre. Et si vous voyagez avec plusieurs enfants, choisissez votre préféré. Votre gilet de sauvetage est sous votre siège. Ne le gonflez qu'à l'extérieur de l'appareil. Enfin, il est interdit de fumer à bord, y compris dans les toilettes, et nos détecteurs sont très vigilants. Merci de votre attention, et bon vol avec {EW}.",
     "en": "There are four emergency exits, two at the front, two at the back. They are marked by lights along the floor. Don't worry, the aircraft is symmetrical. Seat belts: insert the tab into the buckle to fasten, and open the buckle to release. Yes, exactly like in a car. In case of depressurisation, oxygen masks will drop automatically. Pull a mask towards you, place it over your nose and mouth, and breathe normally. If you are travelling with a child, put your own mask on first. And if you are travelling with several children, choose your favourite. Your life jacket is under your seat. Inflate it only once you are outside the aircraft. Finally, smoking is prohibited on board, including in the lavatories, and our detectors are very vigilant. Thank you for your attention, and enjoy your flight with {EW}.",
     "de": "Es gibt vier Notausgänge, zwei vorne und zwei hinten. Sie sind durch Lichtleisten am Boden markiert. Keine Sorge, das Flugzeug ist symmetrisch. Der Sicherheitsgurt: Sie schließen ihn, indem Sie die Zunge in die Schnalle stecken, und öffnen ihn, indem Sie die Schnalle öffnen. Ja, genau wie im Auto. Bei Druckverlust fallen automatisch Sauerstoffmasken herab. Ziehen Sie an einer Maske, setzen Sie sie auf Nase und Mund, und atmen Sie normal. Wenn Sie mit einem Kind reisen, setzen Sie zuerst Ihre eigene Maske auf. Und wenn Sie mit mehreren Kindern reisen, wählen Sie Ihr Lieblingskind aus. Ihre Schwimmweste befindet sich unter Ihrem Sitz. Blasen Sie sie erst außerhalb des Flugzeugs auf. Schließlich ist das Rauchen an Bord verboten, auch in den Toiletten, und unsere Detektoren sind sehr wachsam. Vielen Dank für Ihre Aufmerksamkeit, und einen guten Flug mit {EW}.",
     "es": "Hay cuatro salidas de emergencia, dos en la parte delantera y dos en la trasera. Están señaladas por bandas luminosas en el suelo. No se preocupen, el avión es simétrico. El cinturón: se abrocha insertando la lengüeta en la hebilla, y se desabrocha abriendo la hebilla. Sí, exactamente como en un coche. En caso de despresurización, las máscaras de oxígeno caerán automáticamente. Tire de una máscara, colóquela sobre la nariz y la boca, y respire con normalidad. Si viaja con un niño, póngase primero la suya. Y si viaja con varios niños, elija a su preferido. Su chaleco salvavidas está bajo su asiento. Ínflelo solo fuera de la aeronave. Por último, está prohibido fumar a bordo, incluso en los baños, y nuestros detectores son muy vigilantes. Gracias por su atención, y buen vuelo con {EW}."},
    {"fr": "Cette démonstration dure deux minutes, et elle est plus utile que la plupart des réunions de votre semaine. Les sorties de secours : repérez la plus proche, et comptez les rangées qui vous séparent d'elle. Ça fait de l'exercice, au moins. Elles sont signalées par des bandes lumineuses au sol. Le gilet de sauvetage se trouve sous votre siège, pas dans le coffre à bagages, oui, on nous l'a déjà demandé. Ne le gonflez qu'une fois dehors. En cas de dépressurisation, les masques à oxygène tombent du plafond. Même si le sac ne se gonfle pas, l'oxygène circule, c'est normal. Si vous accompagnez un enfant, ou une personne qui a besoin d'aide, équipez-vous d'abord vous-même. Les appareils électroniques doivent rester en mode avion, c'est pour que vous profitiez enfin de quelques heures sans réunion. Il est interdit de fumer, cigarettes électroniques comprises. Merci, et excellent vol à bord de {EW}.",
     "en": "This demonstration takes two minutes, and it is more useful than most of your meetings this week. Emergency exits: locate the nearest one, and count the rows between you and it. It is good exercise, at least. They are marked by lights along the floor. Your life jacket is under your seat, not in the overhead locker. Yes, we have been asked before. Inflate it only once you are outside. In case of depressurisation, oxygen masks will drop from the ceiling. Even if the bag does not inflate, oxygen is flowing, that is normal. If you are travelling with a child, or someone who needs assistance, fit your own mask first. Electronic devices must stay in flight mode, so you can finally enjoy a few hours without meetings. Smoking is prohibited, including electronic cigarettes. Thank you, and enjoy your flight on board {EW}.",
     "de": "Diese Vorführung dauert zwei Minuten und ist nützlicher als die meisten Besprechungen Ihrer Woche. Die Notausgänge: Suchen Sie den nächstgelegenen, und zählen Sie die Reihen bis dorthin. Das ist immerhin etwas Bewegung. Sie sind durch Lichtleisten am Boden markiert. Die Schwimmweste befindet sich unter Ihrem Sitz, nicht im Gepäckfach – ja, das wurde uns schon gefragt. Blasen Sie sie erst auf, wenn Sie draußen sind. Bei Druckverlust fallen die Sauerstoffmasken von der Decke. Auch wenn sich der Beutel nicht füllt, fließt Sauerstoff, das ist normal. Wenn Sie ein Kind begleiten, oder eine Person, die Hilfe benötigt, setzen Sie zuerst Ihre eigene Maske auf. Elektronische Geräte müssen im Flugmodus bleiben, damit Sie endlich ein paar Stunden ohne Meeting genießen können. Rauchen ist verboten, auch elektronische Zigaretten. Vielen Dank, und einen ausgezeichneten Flug mit {EW}.",
     "es": "Esta demostración dura dos minutos, y es más útil que la mayoría de las reuniones de su semana. Las salidas de emergencia: localice la más cercana, y cuente las filas que lo separan de ella. Al menos es algo de ejercicio. Están señaladas por bandas luminosas en el suelo. El chaleco salvavidas está bajo su asiento, no en el compartimento superior, sí, ya nos lo han preguntado. Ínflelo solo una vez fuera. En caso de despresurización, las máscaras de oxígeno caen del techo. Aunque la bolsa no se infle, el oxígeno circula, es normal. Si acompaña a un niño, o a una persona que necesite ayuda, colóquese primero su propia máscara. Los dispositivos electrónicos deben permanecer en modo avión, para que disfrute por fin de unas horas sin reuniones. Está prohibido fumar, incluidos los cigarrillos electrónicos. Gracias, y excelente vuelo a bordo de {EW}."},
    {"fr": "Pour votre sécurité, voici quelques informations à retenir. Si vous ne devez retenir qu'une chose : la sortie la plus proche est peut-être derrière vous. Vous l'avez repérée ? Parfait. Les sorties sont indiquées par des lumières vertes. Pour attacher votre ceinture, insérez la languette dans la boucle. Pour la détacher, ouvrez la boucle, ce n'est pas un test d'intelligence. En cas de dépressurisation, un masque tombera devant vous. Tirez dessus, placez-le sur le visage, et respirez normalement. Les gilets de sauvetage sont sous les sièges. Ne les gonflez qu'à l'extérieur de l'avion, sinon vous aurez du mal à sortir, et ça gâchera l'effet. Il est strictement interdit de fumer. Si vous avez des questions, notre équipage se fera un plaisir d'y répondre, sauf celle de savoir si le repas est inclus. Merci, et bon vol avec {EW}.",
     "en": "For your safety, here is some information worth remembering. If you only remember one thing: the nearest exit may be behind you. Have you spotted it? Perfect. Exits are marked by green lights. To fasten your seat belt, insert the tab into the buckle. To release it, open the buckle. It is not an intelligence test. In case of depressurisation, a mask will drop in front of you. Pull it towards you, place it over your face, and breathe normally. Life jackets are under the seats. Inflate them only outside the aircraft, otherwise you will have trouble getting out, and it will spoil the effect. Smoking is strictly prohibited. If you have any questions, our crew will be happy to answer, except whether the meal is included. Thank you, and enjoy your flight with {EW}.",
     "de": "Für Ihre Sicherheit hier einige wichtige Informationen. Wenn Sie sich nur eines merken sollen: Der nächste Ausgang könnte hinter Ihnen sein. Haben Sie ihn gefunden? Perfekt. Die Ausgänge sind durch grüne Lichter markiert. Um Ihren Gurt zu schließen, stecken Sie die Zunge in die Schnalle. Um ihn zu öffnen, öffnen Sie die Schnalle – das ist kein Intelligenztest. Bei Druckverlust fällt eine Maske vor Ihnen herab. Ziehen Sie daran, setzen Sie sie auf Ihr Gesicht, und atmen Sie normal. Die Schwimmwesten befinden sich unter den Sitzen. Blasen Sie sie erst außerhalb des Flugzeugs auf, sonst kommen Sie schwer heraus, und der Effekt wäre verdorben. Rauchen ist strikt verboten. Falls Sie Fragen haben, beantwortet unsere Crew diese gerne, außer ob die Mahlzeit inklusive ist. Vielen Dank, und einen guten Flug mit {EW}.",
     "es": "Por su seguridad, aquí tienen algo de información que recordar. Si solo recuerdan una cosa: la salida más cercana puede estar detrás de ustedes. ¿La han localizado? Perfecto. Las salidas están señaladas con luces verdes. Para abrocharse el cinturón, inserte la lengüeta en la hebilla. Para desabrocharlo, abra la hebilla, no es una prueba de inteligencia. En caso de despresurización, una máscara caerá frente a usted. Tire de ella, colóquela sobre el rostro, y respire con normalidad. Los chalecos salvavidas están bajo los asientos. Ínflelos solo fuera del avión, de lo contrario le costará salir, y se estropeará el efecto. Está estrictamente prohibido fumar. Si tienen alguna pregunta, nuestra tripulación responderá con gusto, salvo si la comida está incluida. Gracias, y buen vuelo con {EW}."},
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
    {"fr": "Mesdames et messieurs, la cabine va être plongée dans la pénombre. Rassurez-vous, ce n'est pas pour une soirée cinéma.",
     "en": "Ladies and gentlemen, the cabin lights will now be dimmed. Don't worry, it is not movie night.",
     "de": "Meine Damen und Herren, die Kabine wird nun abgedunkelt. Keine Sorge, es ist kein Kinoabend.",
     "es": "Señoras y señores, la cabina quedará en penumbra. No se preocupen, no es una sesión de cine."},
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
    {"fr": "Mesdames et messieurs, le commandant et tout l'équipage vous souhaitent un agréable vol sur ce {EW} {FN}. Nous serons à {DEST} dans environ {DUR}. Là-bas, la température est de {TEMP_D}, avec {WIND_D}. {COMMENT_D} {TURB} Vous pouvez dès maintenant ranger les manteaux, ou les ressortir, selon la destination. Merci.",
     "en": "Ladies and gentlemen, the captain and the whole crew wish you a pleasant flight on this {EW} {FN}. We will be in {DEST} in about {DUR}. There, the temperature is {TEMP_D}, with {WIND_D}. {COMMENT_D} {TURB} You may put your coats away now, or take them out again, depending on the destination. Thank you.",
     "de": "Meine Damen und Herren, der Kapitän und die gesamte Crew wünschen Ihnen einen angenehmen Flug mit diesem {EW} {FN}. Wir werden in etwa {DUR} in {DEST} sein. Dort beträgt die Temperatur {TEMP_D}, mit {WIND_D}. {COMMENT_D} {TURB} Sie können Ihre Mäntel jetzt wegräumen, oder wieder herausholen, je nach Reiseziel. Vielen Dank.",
     "es": "Señoras y señores, el comandante y toda la tripulación les desean un agradable vuelo en este {EW} {FN}. Estaremos en {DEST} en aproximadamente {DUR}. Allí, la temperatura es de {TEMP_D}, con {WIND_D}. {COMMENT_D} {TURB} Ya pueden guardar los abrigos, o volver a sacarlos, según el destino. Gracias."},
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
    {"fr": "Mesdames et messieurs, nous traversons une zone un peu agitée. Ce n'est pas nous, c'est l'air. Veuillez regagner votre place et attacher votre ceinture.",
     "en": "Ladies and gentlemen, we are passing through a slightly bumpy area. It is not us, it is the air. Please return to your seat and fasten your seat belt.",
     "de": "Meine Damen und Herren, wir fliegen durch eine etwas unruhige Zone. Das sind nicht wir, das ist die Luft. Bitte kehren Sie zu Ihrem Platz zurück und schließen Sie Ihren Sicherheitsgurt.",
     "es": "Señoras y señores, estamos atravesando una zona algo turbulenta. No somos nosotros, es el aire. Regresen a su asiento y abróchense el cinturón."},
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
    {"fr": "Mesdames et messieurs, le signal ceinture vient de s'éteindre. Vous êtes libres de vous déplacer. Les toilettes sont à l'avant et à l'arrière, et oui, il y aura la queue.",
     "en": "Ladies and gentlemen, the seat belt sign is now off. You are free to move around. The lavatories are at the front and the rear, and yes, there will be a queue.",
     "de": "Meine Damen und Herren, das Anschnallzeichen ist soeben ausgegangen. Sie können sich frei bewegen. Die Toiletten befinden sich vorne und hinten, und ja, es wird eine Warteschlange geben.",
     "es": "Señoras y señores, la señal de cinturón se acaba de apagar. Son libres de desplazarse. Los baños están en la parte delantera y trasera, y sí, habrá cola."},
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
])
add("DescentStarted", True, True, [
    {"fr": "Mesdames et messieurs, nous avons commencé notre descente vers {DEST}. À {DEST}, il fait {TEMP_D}, {SKY_D}. {COMMENT_D} Veuillez regagner votre siège, attacher votre ceinture, relever votre tablette et remettre votre dossier en position verticale. Merci.",
     "en": "Ladies and gentlemen, we have started our descent into {DEST}. In {DEST}, it is {TEMP_D}, {SKY_D}. {COMMENT_D} Please return to your seat, fasten your seat belt, stow your tray table, and return your seat back to the upright position. Thank you.",
     "de": "Meine Damen und Herren, wir haben unseren Sinkflug nach {DEST} begonnen. In {DEST} ist es {TEMP_D}, {SKY_D}. {COMMENT_D} Bitte kehren Sie zu Ihrem Sitz zurück, schließen Sie Ihren Sicherheitsgurt, klappen Sie Ihren Tisch hoch und stellen Sie Ihre Rückenlehne aufrecht. Vielen Dank.",
     "es": "Señoras y señores, hemos iniciado nuestro descenso hacia {DEST}. En {DEST} hace {TEMP_D}, {SKY_D}. {COMMENT_D} Regresen a su asiento, abróchense el cinturón, suban su mesita y coloquen el respaldo en posición vertical. Gracias."},
    {"fr": "Mesdames et messieurs, nous allons bientôt atterrir à {DEST}. Température au sol : {TEMP_D}, avec {WIND_D}. Merci de regagner votre place, de relever votre tablette, et de ranger tout ce qui traîne. Oui, cela inclut le dernier biscuit.",
     "en": "Ladies and gentlemen, we will shortly be landing in {DEST}. The temperature on the ground is {TEMP_D}, with {WIND_D}. Please return to your seat, stow your tray table, and put away anything lying around. Yes, that includes the last biscuit.",
     "de": "Meine Damen und Herren, wir werden in Kürze in {DEST} landen. Bodentemperatur: {TEMP_D}, mit {WIND_D}. Bitte kehren Sie zu Ihrem Platz zurück, klappen Sie Ihren Tisch hoch, und verstauen Sie alles, was herumliegt. Ja, das schließt den letzten Keks mit ein.",
     "es": "Señoras y señores, en breve aterrizaremos en {DEST}. Temperatura en tierra: {TEMP_D}, con {WIND_D}. Regresen a su asiento, suban su mesita, y guarden todo lo que tengan suelto. Sí, eso incluye la última galleta."},
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
    {"fr": "Mesdames et messieurs, nous venons d'atterrir à {DEST}. {COMMENT_D} Restez assis jusqu'à l'extinction du signal ceinture. Nous savons que vous êtes tous pressés de récupérer vos bagages, mais ils ne partiront pas sans vous. Merci.",
     "en": "Ladies and gentlemen, we have just landed in {DEST}. {COMMENT_D} Please remain seated until the seat belt sign has been switched off. We know you are all keen to collect your luggage, but it will not leave without you. Thank you.",
     "de": "Meine Damen und Herren, wir sind soeben in {DEST} gelandet. {COMMENT_D} Bleiben Sie sitzen, bis das Anschnallzeichen erlischt. Wir wissen, dass Sie alle Ihr Gepäck holen möchten, aber es wird nicht ohne Sie abfahren. Vielen Dank.",
     "es": "Señoras y señores, acabamos de aterrizar en {DEST}. {COMMENT_D} Permanezcan sentados hasta que se apague la señal de cinturón. Sabemos que todos tienen prisa por recoger su equipaje, pero no se irá sin ustedes. Gracias."},
    {"fr": "Mesdames et messieurs, bienvenue à {DEST}. Il y fait {TEMP_D}, {SKY_D}. Merci de rester assis, ceinture attachée, jusqu'à l'arrêt complet. Ensuite, vous pourrez vous lever tous en même temps, comme d'habitude.",
     "en": "Ladies and gentlemen, welcome to {DEST}. It is {TEMP_D} there, {SKY_D}. Please remain seated with your seat belt fastened until we have come to a complete stop. After that, you may all stand up at the same time, as usual.",
     "de": "Meine Damen und Herren, willkommen in {DEST}. Dort ist es {TEMP_D}, {SKY_D}. Bitte bleiben Sie sitzen, mit angelegtem Sicherheitsgurt, bis zum vollständigen Stillstand. Danach können Sie alle gleichzeitig aufstehen, wie immer.",
     "es": "Señoras y señores, bienvenidos a {DEST}. Allí hace {TEMP_D}, {SKY_D}. Permanezcan sentados, con el cinturón abrochado, hasta la parada completa. Después, podrán levantarse todos a la vez, como siempre."},
])
add("DeboardingStarted", True, True, [
    {"fr": "Mesdames et messieurs, le débarquement commence. N'oubliez pas vos affaires personnelles. Et si vous avez laissé quelque chose derrière vous, ce n'est pas grave, vous reviendrez. Merci d'avoir volé avec {EW}, nous espérons vous revoir très bientôt.",
     "en": "Ladies and gentlemen, deboarding is now starting. Please do not forget your personal belongings. And if you leave something behind, never mind, you will come back. Thank you for flying with {EW}, we hope to see you again very soon.",
     "de": "Meine Damen und Herren, das Aussteigen beginnt. Vergessen Sie bitte nicht Ihre persönlichen Gegenstände. Und falls Sie etwas zurücklassen, ist das nicht schlimm, Sie kommen ja wieder. Vielen Dank, dass Sie mit {EW} geflogen sind, wir hoffen, Sie bald wiederzusehen.",
     "es": "Señoras y señores, comienza el desembarque. No olviden sus pertenencias personales. Y si dejan algo atrás, no se preocupen, volverán. Gracias por volar con {EW}, esperamos verles de nuevo muy pronto."},
    {"fr": "Mesdames et messieurs, vous pouvez maintenant quitter l'appareil. Merci de vérifier que vous avez bien tout pris, y compris vos enfants. L'équipage de ce vol {FN} vous remercie, et vous souhaite un excellent séjour à {DEST}.",
     "en": "Ladies and gentlemen, you may now leave the aircraft. Please check that you have everything, including your children. The crew of flight {FN} thanks you, and wishes you an excellent stay in {DEST}.",
     "de": "Meine Damen und Herren, Sie können das Flugzeug nun verlassen. Bitte überprüfen Sie, dass Sie alles mitgenommen haben, einschließlich Ihrer Kinder. Die Crew von Flug {FN} bedankt sich und wünscht Ihnen einen ausgezeichneten Aufenthalt in {DEST}.",
     "es": "Señoras y señores, ya pueden abandonar la aeronave. Comprueben que han recogido todo, incluidos sus hijos. La tripulación del vuelo {FN} les agradece y les desea una excelente estancia en {DEST}."},
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
    {"fr": "Mesdames et messieurs de l'équipage, tous les passagers ont quitté l'appareil. Merci, et bon repos.",
     "en": "Crew, all passengers have left the aircraft. Thank you, and have a good rest.",
     "de": "Liebe Crew, alle Passagiere haben das Flugzeug verlassen. Danke, und gute Erholung.",
     "es": "Compañeros de tripulación, todos los pasajeros han abandonado la aeronave. Gracias, y buen descanso."},
])
add("Decompression", True, False, [
    {"fr": "Mesdames et messieurs, la pression dans la cabine a chuté. Restez calmes. Les masques à oxygène sont tombés. Tirez sur le masque le plus proche, placez-le sur le nez et la bouche, et respirez normalement. Éteignez toute cigarette. Restez assis, et suivez les instructions de l'équipage.",
     "en": "Ladies and gentlemen, the cabin pressure has dropped. Please remain calm. The oxygen masks have been released. Pull the nearest mask towards you, place it over your nose and mouth, and breathe normally. Extinguish all cigarettes. Remain seated, and follow the instructions of the crew.",
     "de": "Meine Damen und Herren, der Kabinendruck ist gefallen. Bleiben Sie ruhig. Die Sauerstoffmasken sind herabgefallen. Ziehen Sie an der nächsten Maske, setzen Sie sie auf Nase und Mund, und atmen Sie normal. Löschen Sie alle Zigaretten. Bleiben Sie sitzen, und folgen Sie den Anweisungen der Crew.",
     "es": "Señoras y señores, la presión en la cabina ha caído. Mantengan la calma. Las máscaras de oxígeno han caído. Tire de la máscara más cercana, colóquela sobre la nariz y la boca, y respire con normalidad. Apaguen todos los cigarrillos. Permanezcan sentados, y sigan las instrucciones de la tripulación."},
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


PA = ("highpass=f=180,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3000:t=q:w=1:g=1.5,lowpass=f=9000,"
      "acompressor=threshold=-22dB:ratio=2.5:attack=8:release=200,aecho=0.8:0.4:25:0.07,loudnorm=I=-18:TP=-2")


def assemble(clips, carillon, sortie_ogg, tmp):
    """clips : liste d'un ou deux mp3 (langue principale, puis langue secondaire si presente)."""
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
    f = ";".join("[%d:a]aresample=24000,aformat=channel_layouts=mono[a%d]" % (i, i) for i in idx)
    f += ";" + "".join("[a%d]" % i for i in idx) + "concat=n=%d:v=0:a=1,%s[o]" % (len(idx), PA)
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
                await asyncio.get_event_loop().run_in_executor(None, assemble, clips, carillon, sortie, tmpb)
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
    m = {"dependencies": [], "content_type": "MISC", "title": "Eurowings cabin announcements (Fenix A320 airline packs)",
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
        m_o, m_d = metar_frais(icao_o), metar_frais(icao_d)
        ctx = contexte(plan, m_o, m_d)
        sig = signature_meteo(parse_metar(m_d or plan["destination"].get("metar")))
        print("Vol", plan["general"].get("icao_airline"), plan["general"].get("flight_number"), icao_o, "->", icao_d,
              "|", len(profils), "profils | mode", mode, "| METAR", "frais" if m_d else "du plan SimBrief")
        print("=" * 70)
        print("INSTALLATION EN COURS - NE FERMEZ PAS CETTE FENETRE")
        print("INSTALLATION IN PROGRESS - DO NOT CLOSE THIS WINDOW")
        print("=" * 70)
        _statut("EN COURS - ne fermez pas la fenetre / IN PROGRESS - do not close the window")
        t0 = time.time()
        if mode == "types":
            ok, tot = publie_selection(profils, ctx, noms)
            print("régénéré :", ok, "/", tot)
            ecrit_etat(dict(etat, quand=time.strftime("%d/%m/%Y %H:%M")))
        elif mode == "meteo":
            a_faire = types_meteo(("{TEMP_D", "{SKY_D", "{WIND_D", "{COMMENT_D"))
            if etat.get("meteo_origine"):
                a_faire += [n for n in types_meteo(("{TEMP_O", "{SKY_O", "{WIND_O", "{COMMENT_O")) if n not in a_faire]
            ok, tot = publie_selection(profils, ctx, a_faire)
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
                ok, tot = asyncio.run(genere(profils, [e for e in T if not e[2]], ctx, generique))
                print("génériques :", ok, "/", tot)
            shutil.rmtree(perso, ignore_errors=True)
            ok, tot = asyncio.run(genere(profils, [e for e in T if e[2]], ctx, perso))
            print("du vol :", ok, "/", tot)
            tout = os.path.join(WORK, "assemble"); shutil.rmtree(tout, ignore_errors=True); os.makedirs(tout)
            for d in (generique, perso):
                for f in os.listdir(d):
                    shutil.copy2(os.path.join(d, f), os.path.join(tout, f))
            combler(tout, profils)
            publie(tout)
            ecrit_etat({"plan": cle, "vol": "%s%s" % (plan["general"].get("icao_airline", ""), plan["general"].get("flight_number", "")),
                        "de": icao_o, "vers": icao_d, "nb_profils": len(profils), "fichiers": len(os.listdir(tout)),
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


def surveillance_simconnect(arreter=None):
    """Boucle de surveillance automatique via SimConnect : tant qu'un vol est
    detecte dans la simulation (MSFS lance ET un avion charge, pas juste le
    menu principal), regenere les annonces du vol et la meteo automatiquement
    - equivalent de --boucle, mais declenche par l'etat reel du simulateur
    plutot que par une simple minuterie. arreter (threading.Event) permet de
    stopper la boucle depuis l'interface graphique ; en mode console, Ctrl+C
    fonctionne aussi."""
    print("=" * 70)
    print("Eurowings Cabin Announcements V3 - surveillance SimConnect (automatique)")
    print("Connexion a SimConnect... (necessite que MSFS 2024 soit lance)")
    print("Fermez cette fenetre pour arreter. Ctrl+C fonctionne aussi.")
    print("=" * 70)
    sm = None
    aq = None
    en_vol_avant = None
    echecs = 0
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
                    print("Connecte a SimConnect.")
                except Exception as e:
                    print("SimConnect indisponible (%r). MSFS 2024 est-il lance ? Nouvel essai dans 15s." % e)
                    sm = None
                    aq = None
                    _attendre(15, arreter)
                    continue

            en_vol = aq.get("SIM_ON_GROUND") is not None
            if en_vol:
                echecs = 0
                if en_vol_avant is not True:
                    print("Vol detecte (SimConnect connecte a la simulation).")
                try:
                    executer(["--auto", "--meteo"])
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
                    echecs = 0
                _attendre(15, arreter)
        except KeyboardInterrupt:
            print("Arret demande.")
            break
        except Exception as ex:
            print("[SimConnect] erreur boucle (on reessaie dans 15s) : %r" % ex)
            _attendre(15, arreter)
    try:
        if sm:
            sm.exit()
    except Exception:
        pass


def _chemin_exe_xml():
    """Retrouve EXE.xml de MSFS 2024 a partir du dossier Community choisi
    (meme principe que pour Carriere/Copilote sur le PC de developpement) :
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
    nom_addon = "Eurowings Cabin Announcements V3"
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


def boucle_auto_msfs():
    """Lance par MSFS lui-meme (EXE.xml, --auto-msfs) : surveille les vols
    via SimConnect comme surveillance_simconnect, et se ferme tout seul des
    que MSFS 2024 n'est plus en cours d'execution."""
    print("=" * 70)
    print("Eurowings Cabin Announcements V3 - connexion automatique (lance par MSFS)")
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
    surveillance_simconnect(arreter=arreter)


def lancer_gui():
    """Fenetre graphique affichee quand l'executable est lance sans argument
    (double-clic). Un seul bouton 'Installation' : configure, genere le pack,
    inscrit l'auto-lancement avec MSFS (EXE.xml), puis se ferme toute seule.
    Les vols suivants : le programme se relance et se ferme tout seul avec
    MSFS (voir --auto-msfs / boucle_auto_msfs), sans rien a faire."""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext

    fen = tk.Tk()
    fen.title("Eurowings Cabin Announcements V3 - v%s" % VERSION)
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
    tk.Label(cadre_titre, text="Eurowings Cabin Announcements", fg="#ffffff", bg="#10131a",
             font=("Segoe UI", 15, "bold")).pack(anchor="w")
    tk.Label(cadre_titre, text="Cleardeck Studio - v%s" % VERSION, fg="#f2b705", bg="#10131a",
             font=("Segoe UI", 10)).pack(anchor="w")

    cadre = ttk.Frame(fen, padding=14)
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

    ttk.Label(cadre, text="Nom du commandant / chef de cabine (facultatif)\nCaptain / cabin manager's name (optional)").grid(row=3, column=0, sticky="w", pady=6)
    v_nom = tk.StringVar(value=NOM_EQUIPAGE)
    ttk.Entry(cadre, textvariable=v_nom).grid(row=3, column=1, columnspan=2, sticky="we", pady=6)

    bouton = ttk.Button(cadre, text="Installation / Install")
    bouton.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="we")

    journal = scrolledtext.ScrolledText(cadre, height=12, state="disabled", wrap="word")
    journal.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(14, 0))
    cadre.rowconfigure(6, weight=1)

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

        global SIMBRIEF_ID, COMMUNITY, NOM_EQUIPAGE, LANG, PKG
        SIMBRIEF_ID = pid
        COMMUNITY = dossier
        NOM_EQUIPAGE = v_nom.get().strip()
        LANG = LANGUES[cle_choisie][0]
        PKG = os.path.join(COMMUNITY, "fnx-airline-packs-eurowings")
        _sauve_config({"simbrief_id": SIMBRIEF_ID, "community": COMMUNITY, "langue": LANG, "nom_equipage": NOM_EQUIPAGE})

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

            def fin():
                if erreur:
                    bouton.config(state="normal", text="Installation / Install")
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

    fen.mainloop()
def main():
    argv = sys.argv[1:]
    if not argv:
        lancer_gui()
        return
    if "--boucle" in argv:
        print("=" * 70)
        print("Eurowings Cabin Announcements V3 - mode boucle")
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