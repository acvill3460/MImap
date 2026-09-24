"""
Rigenera i file geografici in ../dati/ a partire da fonti aperte.

Serve solo se cambia l'elenco dei comuni delle due diocesi: la mappa usa
i file gia' pronti e non ha bisogno di questo script per funzionare.

Uso:  pip install shapely   (versione 2.1 o successiva)
      python costruisci_geodati.py

Fonti (licenza CC BY 4.0, attribuzione ISTAT):
  - confini comunali del Piemonte: ISTAT, elaborazione openpolis/geojson-italy
  - circoscrizioni di Torino: sezioni di censimento ISTAT 2011 per area
    sub-comunale, via gabrielepinto/dati-sezioni-elettorali; accorpate
    secondo la riforma del 2016 (9 -> 8, 10 -> 2)
"""

import json
import os
import urllib.request

import shapely
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

QUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(QUI, "_cache")
USCITA = os.path.join(QUI, "..", "dati")

URL_COMUNI = ("https://raw.githubusercontent.com/openpolis/geojson-italy/master/"
              "geojson/limits_R_1_municipalities.geojson")
URL_SEZIONI_TORINO = ("https://raw.githubusercontent.com/gabrielepinto/dati-sezioni-elettorali/"
                      "main/shapefiles_sezioni_elettorali_geojson/precincts_torino_census.geojson")

# Territorio dell'Arcidiocesi di Torino (dalla cartina diocesana: 138 comuni TO, 14 CN, 6 AT).
# Alcuni comuni di confine sono diocesani solo in parte (Cuorgne', Castelnuovo Don Bosco,
# Bra, Savigliano): qui sono inclusi per intero.
COMUNI_TORINO = [
    "Groscavallo", "Chialamberto", "Cantoira", "Balme", "Ala di Stura", "Ceres", "Mezzenile",
    "Monastero di Lanzo", "Coassolo Torinese", "Corio", "Usseglio", "Lemie", "Viù", "Traves",
    "Germagnano", "Pessinetto", "Lanzo Torinese", "Cafasse", "Balangero", "Mathi", "Grosso",
    "Villanova Canavese", "Nole", "Vallo Torinese", "Varisella", "Fiano", "Robassomero",
    "La Cassa", "Givoletto", "Val della Torre", "San Gillio", "Druento", "Venaria Reale",
    "Borgaro Torinese", "Caselle Torinese", "San Maurizio Canavese", "San Francesco al Campo",
    "Ciriè", "San Carlo Canavese", "Front", "Vauda Canavese", "Rivarossa", "Barbania",
    "Rocca Canavese", "Levone", "Rivara", "Busano", "Forno Canavese", "Pratiglione",
    "Prascorsano", "San Colombano Belmonte", "Canischio", "Cuorgnè", "Valperga", "Salassa",
    "Pertusio", "San Ponso", "Oglianico", "Favria", "Leini", "Volpiano", "Brandizzo", "Mappano",
    "Settimo Torinese", "San Raffaele Cimena", "Castagneto Po", "San Sebastiano da Po",
    "Lauriano", "Casalborgone", "Rivalba", "Gassino Torinese", "Castiglione Torinese",
    "San Mauro Torinese", "Sciolze", "Cinzano", "Berzano di San Pietro", "Aramengo",
    "Passerano Marmorito", "Moncucco Torinese", "Baldissero Torinese", "Pavarolo",
    "Montaldo Torinese", "Marentino", "Mombello di Torino", "Moriondo Torinese",
    "Castelnuovo Don Bosco", "Pino Torinese", "Andezeno", "Arignano", "Buttigliera d'Asti",
    "Chieri", "Pecetto Torinese", "Riva presso Chieri", "Poirino", "Cambiano", "Santena",
    "Trofarello", "Moncalieri", "Villastellone", "Carmagnola", "Torino", "Caselette",
    "Alpignano", "Pianezza", "Collegno", "Grugliasco", "Rivoli", "Rosta", "Buttigliera Alta",
    "Avigliana", "Valgioie", "Coazze", "Giaveno", "Reano", "Villarbasse", "Trana", "Sangano",
    "Bruino", "Rivalta di Torino", "Beinasco", "Orbassano", "Piossasco", "Cumiana", "Volvera",
    "Nichelino", "Candiolo", "Vinovo", "La Loggia", "None", "Airasca", "Piscina", "Scalenghe",
    "Piobesi Torinese", "Carignano", "Castagnole Piemonte", "Virle Piemonte", "Osasio",
    "Lombriasco", "Cercenasco", "Vigone", "Pancalieri", "Garzigliana", "Cavour",
    "Villafranca Piemonte", "Casalgrasso", "Faule", "Polonghera", "Moretta", "Murello",
    "Racconigi", "Caramagna Piemonte", "Sommariva del Bosco", "Sanfrè", "Bra", "Cavallerleone",
    "Cavallermaggiore", "Marene", "Savigliano",
]

# Territorio della Diocesi di Susa (le 9 vicarie: 35 comuni).
COMUNI_SUSA = [
    "Bardonecchia", "Chiomonte", "Exilles", "Oulx", "Salbertrand", "Sauze d'Oulx",
    "Cesana Torinese", "Claviere", "Sauze di Cesana", "Sestriere", "Susa", "Gravere",
    "Meana di Susa", "Mompantero", "Giaglione", "Moncenisio", "Novalesa", "Venaus", "Bruzolo",
    "Bussoleno", "Chianocco", "Mattie", "San Didero", "San Giorio di Susa", "Borgone Susa",
    "Caprie", "Condove", "Chiusa di San Michele", "Sant'Ambrogio di Torino",
    "Sant'Antonino di Susa", "Vaie", "Villar Focchiardo", "Almese", "Rubiana", "Villar Dora",
]

# Circoscrizioni dal 2016: codice ISTAT 2011 -> circoscrizione attuale
ACCORPAMENTI_2016 = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 8, "10": 2}
NOMI_CIRCOSCRIZIONI = {
    1: "Centro, Crocetta",
    2: "Santa Rita, Mirafiori Nord, Mirafiori Sud",
    3: "San Paolo, Cenisia, Pozzo Strada, Cit Turin, Borgata Lesna",
    4: "San Donato, Campidoglio, Parella",
    5: "Borgo Vittoria, Madonna di Campagna, Lucento, Vallette",
    6: "Barriera di Milano, Regio Parco, Barca, Bertolla, Falchera, Rebaudengo, Villaretto",
    7: "Aurora, Vanchiglia, Sassi, Madonna del Pilone",
    8: "San Salvario, Cavoretto, Borgo Po, Nizza Millefonti, Lingotto, Filadelfia",
}

TOLLERANZA_COMUNI = 0.0006        # gradi, circa 50 m: invisibile fino allo zoom 12
TOLLERANZA_CIRCOSCRIZIONI = 0.00012
DECIMALI = 5


def scarica(url, nome):
    os.makedirs(CACHE, exist_ok=True)
    percorso = os.path.join(CACHE, nome)
    if not os.path.exists(percorso):
        print("Scarico", url)
        urllib.request.urlretrieve(url, percorso)
    with open(percorso, encoding="utf-8") as f:
        return json.load(f)


def arrotonda(geom):
    return shapely.set_precision(geom, 10 ** -DECIMALI)


def punto_etichetta(geom):
    """Punto dove mettere etichetta e segnaposto: il baricentro, se cade dentro."""
    c = geom.centroid
    p = c if geom.contains(c) else geom.representative_point()
    return [round(p.y, DECIMALI), round(p.x, DECIMALI)]


def pulisci(geom, minimo=1e-6, chiudi_fessure=True):
    """Toglie buchi e frammenti microscopici (e, se richiesto, le fessure tra poligoni)."""
    if chiudi_fessure:
        geom = geom.buffer(0.00002).buffer(-0.00002)
    parti = [g for g in getattr(geom, "geoms", [geom]) if g.area > minimo]
    parti = [shapely.Polygon(p.exterior, [r for r in p.interiors if shapely.Polygon(r).area > minimo])
             for p in parti]
    return unary_union(parti)


def feature(geom, proprieta):
    return {"type": "Feature", "properties": proprieta, "geometry": mapping(geom)}


def scrivi(nome, oggetto):
    percorso = os.path.join(USCITA, nome)
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(oggetto, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{nome}: {os.path.getsize(percorso) / 1024:.0f} KB")


def main():
    os.makedirs(USCITA, exist_ok=True)
    piemonte = scarica(URL_COMUNI, "comuni_piemonte.geojson")["features"]
    per_nome = {f["properties"]["name"]: f for f in piemonte}

    diocesi_di = {n: "Torino" for n in COMUNI_TORINO}
    diocesi_di.update({n: "Susa" for n in COMUNI_SUSA})
    mancanti = [n for n in diocesi_di if n not in per_nome]
    if mancanti:
        raise SystemExit(f"Nomi non trovati tra i comuni ISTAT: {mancanti}")

    # 1. Comuni delle due diocesi, semplificati mantenendo i confini condivisi
    nomi = list(diocesi_di)
    geometrie = [shape(per_nome[n]["geometry"]).buffer(0) for n in nomi]
    semplificate = shapely.coverage_simplify(geometrie, TOLLERANZA_COMUNI)
    elementi = []
    for nome, originale, g in zip(nomi, geometrie, semplificate):
        elementi.append(feature(arrotonda(g), {
            "tipo": "comune",
            "nome": nome,
            "istat": per_nome[nome]["properties"]["com_istat_code"],
            "diocesi": diocesi_di[nome],
            "lp": punto_etichetta(originale),
        }))
    for diocesi in ("Torino", "Susa"):
        unione = pulisci(unary_union([g for n, g in zip(nomi, geometrie) if diocesi_di[n] == diocesi]))
        contorno = unione.simplify(TOLLERANZA_COMUNI)
        elementi.append(feature(arrotonda(contorno), {
            "tipo": "diocesi", "nome": diocesi, "lp": punto_etichetta(unione)}))
    scrivi("territorio.geojson", {"type": "FeatureCollection", "features": elementi})

    # 2. Circoscrizioni di Torino (8, dal 2016)
    sezioni = scarica(URL_SEZIONI_TORINO, "sezioni_torino_2011.geojson")["features"]
    gruppi = {}
    for s in sezioni:
        numero = ACCORPAMENTI_2016[str(s["properties"]["COD_ASC"])]
        gruppi.setdefault(numero, []).append(shape(s["geometry"]).buffer(0))
    numeri = sorted(gruppi)
    unite = [pulisci(unary_union(gruppi[n]), minimo=2e-5, chiudi_fessure=False) for n in numeri]
    # Nei dati 2011 una sezione della 7 cade dentro la 1: i frammenti piccoli
    # racchiusi da un'altra circoscrizione passano a quella che li contiene.
    for i, g in enumerate(unite):
        tenute = []
        for parte in getattr(g, "geoms", [g]):
            dentro_altra = parte.area < 2e-5 and any(
                j != i and altra.buffer(1e-5).contains(parte) for j, altra in enumerate(unite))
            if not dentro_altra:
                tenute.append(parte)
        unite[i] = unary_union(tenute)
    semplificate = shapely.coverage_simplify(unite, TOLLERANZA_CIRCOSCRIZIONI)
    circoscrizioni = [feature(arrotonda(g), {
        "numero": n, "nome": NOMI_CIRCOSCRIZIONI[n], "lp": punto_etichetta(u)})
        for n, u, g in zip(numeri, unite, semplificate)]
    scrivi("torino-circoscrizioni.geojson", {"type": "FeatureCollection", "features": circoscrizioni})

    # 3. Punto di riferimento di tutti i comuni piemontesi, per riconoscere
    #    anche comuni scritti nel foglio ma fuori dall'elenco diocesano
    punti = sorted([f["properties"]["name"], *punto_etichetta(shape(f["geometry"]).buffer(0))]
                   for f in piemonte)
    scrivi("comuni-piemonte.json", punti)


if __name__ == "__main__":
    main()
