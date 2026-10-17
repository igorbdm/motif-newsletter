# Cada canal tem:
#   id               ID do canal no YouTube
#   keep / ignore    palavras do título para manter / descartar
#   min_duration     (opcional) duração mínima do vídeo, em segundos
#   section          (opcional) "extras" coloca o canal no Beyond the Stage
#   artist_patterns  (opcional) como achar o nome do artista no título, para
#                    buscar o gênero musical. O nome fica no grupo (?P<artist>…).
#                    Mais de um padrão: vale o primeiro que encaixar. Canais
#                    do Beyond the Stage não precisam, porque não levam selo.

CHANNELS = {
    "KEXP": {
        "id": "UC3I2GFN_F8WudD_2jUZbojA",
        "keep": ["Full Performance"],
        "ignore": [],
        # "Death Cab For Cutie - Full Performance (Live on KEXP)"
        "artist_patterns": [r"^(?P<artist>.+?)\s+-\s+Full Performance"],
    },
    "Tiny Desk": {
        "id": "UC4eYXhJI4-7wSWc8UNRwD4A",
        "keep": ["Tiny Desk Concert"],
        "ignore": [],
        # "Tim Bernardes: Tiny Desk Concert"
        "artist_patterns": [r"^(?P<artist>.+?):\s*Tiny Desk"],
    },
    "Audiotree": {
        "id": "UCWjmAUHmajb1-eo5WKk_22A",
        "keep": ["Full Session"],
        "ignore": [],
        # "Cold Steel on Audiotree Live (Full Session)"
        "artist_patterns": [r"^(?P<artist>.+?)\s+on Audiotree"],
    },
    "La Blogothèque": {
        "id": "UCFAKGci5lneha2x4XMbzYrQ",
        "keep": [],
        "ignore": [],
        "min_duration": 90,
        # "Peter Broderick | The Sounds of Ireland"
        # "Rostam - The Road to Death | Live Session"
        "artist_patterns": [r"^(?P<artist>.+?)(?:\s+-\s+[^|]+)?\s+\|"],
    },
    "KCRW": {
        "id": "UC54U5gpKkaa_BpXRVNip2Dw",
        "keep": ["Live on KCRW"],
        "ignore": [],
        "min_duration": 600,
        # "Sébastien Tellier: Live on KCRW"
        "artist_patterns": [r"^(?P<artist>.+?):\s*Live on KCRW"],
    },
    "Cultura Livre": {
        "id": "UCBuFf6FSDclfDvRGJY1Q5Uw",
        "keep": ["CULTURA LIVRE"],
        "ignore": [],
        "min_duration": 600,
        # "CULTURA LIVRE | Fera Neném | 10/10/26"
        # "Fera Neném no Cultura Livre"
        "artist_patterns": [
            r"^Cultura Livre\s*\|\s*(?P<artist>[^|]+?)\s*\|",
            r"^(?P<artist>.+?)\s+no Cultura Livre",
        ],
    },
    "Amoeba Music": {
        "id": "UC9DkCKm4_VDztRRyge4mCJQ",
        "keep": ["In My Bag"],
        "ignore": [],
        # Não é música ao vivo: aparece em uma seção separada no fim do e-mail.
        "section": "extras",
    },
    "Pitchfork": {
        "id": "UC7kI8WjpCfFoMSNDuRh_4lA",
        # Over/Under: "Audrey Hobert Rates Podcasts, Don Toliver, and Disney Adults | Pitchfork".
        # O canal também publica cortes curtos do programa ("Audrey Hobert
        # Rates Don Toliver", com 31 s); a duração mínima deixa só o episódio.
        "keep": ["Rates", "Over/Under"],
        "ignore": [],
        "min_duration": 300,
        "section": "extras",
    },
}
