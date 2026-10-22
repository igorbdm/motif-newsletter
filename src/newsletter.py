from datetime import date, datetime
from html import escape


# Estrutura da edição:
#   1. Cabeçalho (logo, data e abertura)
#   2. Song of the Week (cartão de destaque)
#   3. Live Sessions (performances, agrupadas por canal)
#   4. Compartilhar
#   5. Beyond the Stage (vídeos que não são música ao vivo)
#   6. Rodapé
#
# Compatibilidade com clientes de e-mail: o layout usa apenas tabelas, todo
# espaçamento fica em <td> (o Outlook ignora padding em <div> e <table>) e
# cores de fundo também vão no atributo bgcolor.

# Paleta / estilo
ACCENT = "#f23809"
TEXT_MAIN = "#000000"
TEXT_MUTED = "#6b6b6b"
CHANNEL_COLOR = TEXT_MUTED
HAIRLINE = "#dcdcd7"
BG_PAGE = "#ffffff"
BG_FEATURE = "#f2f2ef"
BG_SOFT = "#faf6eb"  # creme bem leve, como papel pólen
FONT = "'Montserrat', Arial, sans-serif"

LINK_LABELS = {
    "live": "Watch performance →",
    "extras": "Watch video →",
}

STREAMING_LABELS = {
    "spotify": "Spotify",
    "apple_music": "Apple Music",
    "youtube_music": "YouTube Music",
}


def generate_subject(edition_date: date | None = None):
    edition_date = edition_date or datetime.now().date()
    return f"A Week in Music · {edition_date.strftime('%B %d, %Y')}"


def row(content, padding_bottom=40):
    """Uma linha do corpo do e-mail, com as margens laterais padrão."""
    return f"""
  <tr>
    <td class="espacamento-lateral" style="padding:0 32px {padding_bottom}px;">
{content}
    </td>
  </tr>
"""


def label_html(label, description):
    """Rótulo laranja + frase de apoio: abre todas as seções."""
    return f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
        <tr>
          <td style="font-family:{FONT}; font-size:13px; line-height:1.4; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:{ACCENT};">
            {label}
          </td>
        </tr>
        <tr>
          <td style="padding-top:4px; font-family:{FONT}; font-size:14px; line-height:1.5; color:{TEXT_MAIN};">
            {description}
          </td>
        </tr>
      </table>"""


def section_header_html(label, description):
    return f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
        <tr>
          <td style="border-top:2px solid {TEXT_MAIN}; padding-top:20px;">
            {label_html(label, description)}
          </td>
        </tr>
      </table>"""


def header_html(edition_date):
    today = edition_date.strftime("%B %d, %Y")

    return f"""
  <!-- HEADER -->
  <tr>
    <td class="header" style="padding:52px 32px 36px;">
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
        <tr>
          <td class="header-logo" style="font-family:{FONT}; font-size:48px; line-height:1; font-weight:bold; letter-spacing:-3px; color:{TEXT_MAIN};">
            motif.
          </td>
        </tr>
        <tr>
          <td style="padding-top:8px; font-family:{FONT}; font-size:14px; line-height:1.4; color:{TEXT_MAIN};">
            Good Music for Good People.
          </td>
        </tr>
      </table>
    </td>
  </tr>
""" + row(label_html(
        today,
        "Hey everyone! Igor from Motif here. Just a quick one today: we’ve got two new things "
        "in the newsletter. First, a little section where I share a song I’ve been listening to "
        "throughout the week. And second, a new section featuring music-related videos that aren’t "
        "live sessions, but shows and other programs about music, like What’s in My Bag by Amoeba "
        "Music and Over/Under by Pitchfork."
        "<br><br>"
        "Thanks to everyone who sent in suggestions for the newsletter. It’s been really nice "
        "hearing from you, and I’ll have more updates to share soon, too. But for now, I just "
        "wanted to ask you to share Motif with other people who are into music. It really helps "
        "the newsletter grow :)"
        "<br><br>"
        "Cheers, and see you in the next edition!",
    ), padding_bottom=32)


def generate_pick_html(pick):
    """Música recomendada da semana, escolhida a partir do Last.fm.

    Espera um dicionário com "artist" e "title" e, opcionalmente, "album",
    "image" (capa) e "links" (Spotify, Apple Music e YouTube Music).
    """
    artist = escape(str(pick["artist"]))
    title = escape(str(pick["title"]))

    album = ""
    if pick.get("album"):
        album = f"""
                          <tr>
                            <td style="padding-top:10px; font-family:{FONT}; font-size:13px; line-height:1.4; color:{TEXT_MUTED};">
                              {escape(str(pick["album"]))}
                            </td>
                          </tr>"""

    links = ""
    available = [
        (label, pick.get("links", {}).get(platform))
        for platform, label in STREAMING_LABELS.items()
    ]
    available = [(label, url) for label, url in available if url]
    if available:
        separator = f'&nbsp;<span style="color:{TEXT_MUTED};">·</span>&nbsp;'
        anchors = separator.join(
            f'<a href="{escape(str(url), quote=True)}" target="_blank" style="color:{ACCENT}; text-decoration:underline; white-space:nowrap;">{label}</a>'
            for label, url in available
        )
        links = f"""
                          <tr>
                            <td style="padding-top:12px; font-family:{FONT}; font-size:13px; line-height:1.6; font-weight:bold;">
                              {anchors}
                            </td>
                          </tr>"""

    cover = ""
    if pick.get("image"):
        image = escape(str(pick["image"]), quote=True)
        cover = f"""
                <td class="pick-cover" width="112" valign="top" style="width:112px; padding:0 20px 0 0;">
                  <img src="{image}" width="112" height="112" alt="{title}, {artist}" style="display:block; width:112px; height:112px; border:0; outline:none; text-decoration:none;">
                </td>"""

    return "\n  <!-- SONG OF THE WEEK -->" + row(
        section_header_html("Song of the Week", "One song I think deserves a place in your week.")
        + f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
        <tr>
          <td style="padding-top:22px;">
            <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0" bgcolor="{BG_FEATURE}" style="background-color:{BG_FEATURE};">
              <tr>
                <td bgcolor="{BG_FEATURE}" style="padding:20px; background-color:{BG_FEATURE};">
                  <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
                    <tr>{cover}
                      <td class="pick-info" valign="middle">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                          <tr>
                            <td style="font-family:{FONT}; font-size:20px; line-height:1.25; font-weight:bold; color:{TEXT_MAIN};">
                              {title}
                            </td>
                          </tr>
                          <tr>
                            <td style="padding-top:4px; font-family:{FONT}; font-size:16px; line-height:1.35; color:{TEXT_MAIN};">
                              {artist}
                            </td>
                          </tr>{album}{links}
                        </table>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>""")


# Siglas que devem aparecer em maiúsculas no selo de gênero.
GENRE_ACRONYMS = {"mpb": "MPB", "r&b": "R&B", "rnb": "R&B", "idm": "IDM", "edm": "EDM"}


def format_genre(genre):
    """"indie rock" -> "Indie rock", "mpb" -> "MPB"."""
    genre = genre.strip()
    return GENRE_ACRONYMS.get(genre.casefold(), genre[:1].upper() + genre[1:])


def genre_html(video):
    """Selo com o gênero do artista, antes do link. Vazio se não houver.

    Os &nbsp; nas pontas garantem um respiro no Outlook, que ignora padding
    em <span>.
    """
    # O Beyond the Stage não é música ao vivo e não leva selo de gênero.
    if not video.get("genre") or video.get("section") == "extras":
        return ""

    genre = escape(format_genre(str(video["genre"])))

    return f"""<span style="display:inline-block; padding:1px 4px; background-color:{BG_FEATURE}; font-family:{FONT}; font-size:11px; line-height:1.5; font-weight:normal; color:{TEXT_MUTED}; white-space:nowrap;">&nbsp;{genre}&nbsp;</span>&nbsp;&nbsp;
            """


def video_html(video, is_first):
    title = escape(str(video.get("display_title") or video["title"]))
    link = escape(str(video["link"]), quote=True)
    link_label = LINK_LABELS[video.get("section", "live")]
    padding_top = 0 if is_first else 18

    return f"""
        <tr>
          <td style="padding-top:{padding_top}px; font-family:{FONT}; font-size:15px; line-height:1.4; font-weight:bold; color:{TEXT_MAIN};">
            {title}
          </td>
        </tr>
        <tr>
          <td style="padding-top:4px; font-family:{FONT}; font-size:13px; line-height:1.4; font-weight:bold;">
            {genre_html(video)}<a href="{link}" target="_blank" style="color:{ACCENT}; text-decoration:underline;">{link_label}</a>
          </td>
        </tr>"""


def channel_html(channel, videos, is_first):
    # O primeiro canal fica logo abaixo do cabeçalho da seção; os seguintes
    # são separados por um fio fino. O espaçador usa height + font-size:0,
    # que é a forma que o Outlook respeita.
    divider = ""
    if not is_first:
        divider = f"""
        <tr>
          <td height="26" style="height:26px; font-size:0; line-height:0; border-bottom:1px solid {HAIRLINE};">&nbsp;</td>
        </tr>"""

    items = "".join(
        video_html(video, is_first=index == 0)
        for index, video in enumerate(videos)
    )

    return f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">{divider}
        <tr>
          <td style="padding-top:24px; padding-bottom:12px; font-family:{FONT}; font-size:12px; line-height:1.3; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:{CHANNEL_COLOR};">
            {escape(str(channel))}
          </td>
        </tr>{items}
      </table>"""


def group_by_channel(videos):
    groups = {}
    for video in videos:
        groups.setdefault(video["channel"], []).append(video)
    return groups


def video_section_html(comment, label, description, videos):
    channels = "".join(
        channel_html(channel, channel_videos, is_first=index == 0)
        for index, (channel, channel_videos) in enumerate(group_by_channel(videos).items())
    )

    return f"\n  <!-- {comment} -->" + row(
        section_header_html(label, description) + channels
    )


def share_html():
    return "\n  <!-- SHARE / SIGNUP -->" + row(f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0" bgcolor="{BG_SOFT}" style="background-color:{BG_SOFT};">
        <tr>
          <td bgcolor="{BG_SOFT}" style="padding:22px 24px 24px; background-color:{BG_SOFT};">
            <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
              <tr>
                <td style="font-family:{FONT}; font-size:14px; line-height:1.4; font-weight:bold; color:{TEXT_MAIN};">
                  Know someone who might enjoy this? Forward this email to them.
                </td>
              </tr>
              <tr>
                <td style="padding-top:6px; font-family:{FONT}; font-size:13px; line-height:1.5; color:{TEXT_MAIN};">
                  And if someone sent it to you, you can subscribe below.
                </td>
              </tr>
              <tr>
                <td style="padding-top:12px; font-family:{FONT}; font-size:13px; line-height:1.4; font-weight:bold;">
                  <a href="https://motifnewsletter.com" target="_blank" style="color:{ACCENT}; text-decoration:underline;">Subscribe to Motif →</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>""")


def sign_off_html():
    return "\n  <!-- SIGN-OFF -->" + row(f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
        <tr>
          <td style="font-family:{FONT}; font-size:14px; line-height:1.5; color:{TEXT_MAIN};">
            That's all for this week. See you next Friday.
          </td>
        </tr>
      </table>""", padding_bottom=32)


def footer_html():
    return "\n  <!-- FOOTER -->" + row(f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" border="0">
        <tr>
          <td style="border-top:2px solid {TEXT_MAIN}; padding-top:20px; font-family:{FONT}; font-size:12px; line-height:1.5; color:{TEXT_MUTED};">
            You're receiving this because you subscribed to the Motif Newsletter.<br>
            Good Music for Good People.
          </td>
        </tr>
      </table>""", padding_bottom=32)


def generate_html(videos, edition_date: date | None = None, pick=None):
    edition_date = edition_date or datetime.now().date()

    # Vídeos que não são música ao vivo (ex.: "What's In My Bag?") ficam
    # em uma seção própria, depois das performances.
    live_videos = [video for video in videos if video.get("section", "live") != "extras"]
    extra_videos = [video for video in videos if video.get("section") == "extras"]

    body = header_html(edition_date)

    if pick:
        body += generate_pick_html(pick)

    if live_videos:
        body += video_section_html(
            "LIVE SESSIONS",
            "Live Sessions",
            "Full performances published this week by the channels we follow.",
            live_videos,
        )

    # O compartilhamento fecha as performances; os extras vêm depois.
    body += share_html()

    if extra_videos:
        body += video_section_html(
            "BEYOND THE STAGE",
            "Beyond the Stage",
            "Not live music, but still music.",
            extra_videos,
        )

    body += sign_off_html()
    body += footer_html()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>Motif Newsletter</title>

<style type="text/css">
    @font-face {{
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 400;
        src: url('https://fonts.gstatic.com/s/montserrat/v13/JTUSjIg1_i6t8kCHKm459WRhyyTh89ZNpQ.woff2') format('woff2');
    }}

    @font-face {{
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 700;
        src: url('https://fonts.gstatic.com/s/montserrat/v13/JTURjIg1_i6t8kCHKm45_dJE3gTD_vx3rCubqg.woff2') format('woff2');
    }}

    body {{
        margin: 0;
        padding: 0;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
    }}

    table, td {{
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
    }}

    /* Impede o iOS de transformar datas em links azuis. */
    a[x-apple-data-detectors] {{
        color: inherit !important;
        text-decoration: none !important;
    }}

    @media (min-width: 768px) {{
        .body_table {{
            border-left: 8px solid {ACCENT} !important;
        }}

        .espacamento-lateral {{
            padding-left: 78px !important;
            padding-right: 78px !important;
        }}

        .header {{
            padding: 82px 78px 48px !important;
        }}
    }}

    /* No celular, a capa da música fica acima do texto. */
    @media (max-width: 480px) {{
        .pick-cover,
        .pick-info {{
            display: block !important;
            width: 100% !important;
            padding-right: 0 !important;
        }}

        .pick-cover {{
            padding-bottom: 18px !important;
        }}
    }}
</style>
</head>

<body style="margin:0; padding:0; background-color:{BG_PAGE};">

<!--[if mso]><table role="presentation" width="650" align="center" cellspacing="0" cellpadding="0" border="0"><tr><td><![endif]-->
<table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="center" border="0" bgcolor="{BG_PAGE}" style="max-width:650px; background-color:{BG_PAGE};">
<tr>
<td>

<table role="presentation" class="body_table" cellspacing="0" cellpadding="0" width="100%" border="0" bgcolor="{BG_PAGE}" style="background-color:{BG_PAGE}; border-left:5px solid {ACCENT};">
{body}
</table>

</td>
</tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->

</body>
</html>
"""
