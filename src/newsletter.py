from datetime import datetime
from html import escape


def generate_subject():
    return f"Motif Newsletter — {datetime.now().strftime('%d/%m/%Y')}"


def generate_html(videos):
    today = datetime.now().strftime("%d/%m/%Y")

    # Paleta / estilo
    bg_page = "#f0f0f0"
    bg_card = "#ffffff"
    accent = "#e63946"
    channel_color = "#3a3f44"
    text_main = "#333333"
    text_muted = "#6b6b6b"

    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Motif Newsletter</title>
</head>
<body style="margin:0; padding:0; background-color:{bg_page}; font-family: Georgia, 'Times New Roman', serif;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{bg_page};">
<tr>
<td align="center" style="padding: 32px 16px;">

<table role="presentation" width="100%" style="max-width:640px;" cellpadding="0" cellspacing="0">

  <!-- Cabeçalho -->
  <tr>
    <td align="center" style="padding-bottom: 24px;">
      <div style="font-size:13px; letter-spacing:2px; text-transform:uppercase; color:{text_muted}; font-family: Arial, sans-serif;">
        Edição de {today}
      </div>
      <div style="font-size:34px; font-weight:bold; color:{text_main}; margin-top:6px;">
        🎵 Motif Newsletter
      </div>
      <div style="width:60px; height:3px; background-color:{accent}; margin: 16px auto 0;"></div>
    </td>
  </tr>

  <!-- Conteúdo -->
  <tr>
    <td style="background-color:{bg_card}; border-radius:8px; padding: 8px 32px 24px;">
"""

    current_channel = None

    for video in videos:
        channel = escape(str(video["channel"]))
        title = escape(str(video["title"]))
        link = escape(str(video["link"]), quote=True)

        if video["channel"] != current_channel:
            current_channel = video["channel"]
            html += f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top: 28px;">
        <tr>
          <td style="border-bottom: 1px solid #eaeaea; padding-bottom: 6px;">
            <span style="font-family: Arial, sans-serif; font-size:12px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:{channel_color};">
              {channel}
            </span>
          </td>
        </tr>
      </table>
"""

        html += f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding: 14px 0; border-bottom: 1px solid #f0f0f0;">
            <a href="{link}" style="font-family: Arial, sans-serif; font-size:15px; color:{text_main}; text-decoration:none; line-height:1.5;">
              ▸ {title}
            </a>
          </td>
        </tr>
      </table>
"""

    html += f"""
    </td>
  </tr>

  <!-- Separador entre a newsletter e o rodapé padrão do Kit -->
  <tr>
    <td style="padding: 32px 0 8px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="border-top: 1px dashed #d0cfc8; padding-top: 20px; font-family: Arial, sans-serif;">
            <div style="font-size:12px; color:{text_muted};">
              You received this email because you subscribe to the Motif Newsletter 🎵
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""

    return html
