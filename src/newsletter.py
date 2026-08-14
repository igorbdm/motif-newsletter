from datetime import datetime
from html import escape


def generate_subject():
    return f"A Week in Music · {datetime.now().strftime('%B %d, %Y')}"
    

def generate_html(videos):
    today = datetime.now().strftime("%B %d, %Y")

    # Paleta / estilo
    bg_page = "#ffffff"
    bg_card = "#ffffff"
    accent = "#f23809"
    channel_color = "#000000"
    text_main = "#000000"
    text_muted = "#6b6b6b"

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        background-color: #ffffff;
        font-family: 'Montserrat', Arial, sans-serif;
    }}

    .body_table {{
        border-left: 5px solid #f23809;
        background: #ffffff;
    }}

    .espacamento-lateral {{
        padding-left: 32px;
        padding-right: 32px;
    }}

    .header {{
        padding: 52px 0 45px 32px;
    }}

    .header-logo {{
        font-family: 'Montserrat', Arial, sans-serif;
        font-size: 48px;
        line-height: 1;
        font-weight: 700;
        letter-spacing: -3px;
        color: #000000;
    }}

    .section-header {{
        border-top: 2px solid #000000;
        padding-top: 20px;
    }}

    @media (min-width: 768px) {{
        .body_table {{
            border-left: 8px solid #f23809;
        }}

        .espacamento-lateral {{
            padding-left: 78px;
            padding-right: 78px;
        }}

        .header {{
            padding: 82px 0 71px 78px;
        }}
    }}
</style>

</head>

<body style="margin:0; background-color:{bg_page};">

<table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="center" border="0" style="max-width:650px; background:#fff;">
<tr>
<td>

<table role="presentation" class="body_table" cellspacing="0" cellpadding="0" width="100%" align="center" border="0" style="background:#fff; border-left:5px solid {accent};">

  <!-- HEADER -->
  <tr>
    <td>
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="left" border="0" class="header" style="padding:52px 0 45px 32px;">
        <tr>
          <td>
            <div class="header-logo" style="font-family:'Montserrat', Arial, sans-serif; font-size:48px; line-height:1; font-weight:700; letter-spacing:-3px; color:#000000;">
              motif.
            </div>
            <div style="padding-top:8px; color:#000000; font-family:'Montserrat', Arial, sans-serif; font-size:14px; line-height:1.4; letter-spacing:normal; word-spacing:normal; white-space:normal;">
              Good Music for Good People.
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td class="espacamento-lateral" style="padding-bottom:25px; padding-left:32px; padding-right:32px;">
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="left" border="0">
        <tr>
          <td>
            <span style="font-weight:bold; text-transform:uppercase; color:{accent}; font-family:'Montserrat', Arial, sans-serif; font-size:14px;">
              {today}
            </span>
          </td>
        </tr>

        <tr>
          <td style="padding-top:5px; color:{text_main}; font-family:'Montserrat', Arial, sans-serif; font-size:14px; line-height:1.4;">
            A weekly gathering of performances published across the channels we follow.
          </td>
        </tr>
      </table>
    </td>
  </tr>
"""

    current_channel = None

    for video in videos:
        channel = escape(str(video["channel"]))
        title = escape(str(video["title"]))
        link = escape(str(video["link"]), quote=True)

        if video["channel"] != current_channel:
            current_channel = video["channel"]

            html += f"""
  <!-- CHANNEL HEADER -->
  <tr>
    <td class="espacamento-lateral" style="padding-bottom:25px; padding-left:32px; padding-right:32px;">
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="left" border="0" class="section-header" style="border-top:2px solid #000000; padding-top:20px;">
        <tr>
          <td>
            <span style="font-weight:bold; color:{channel_color}; font-family:'Montserrat', Arial, sans-serif; font-size:20px;">
              {channel}
            </span>
          </td>
        </tr>
      </table>
    </td>
  </tr>
"""

        html += f"""
  <!-- VIDEO -->
  <tr>
    <td class="espacamento-lateral" style="padding-bottom:25px; padding-left:32px; padding-right:32px;">
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="left" border="0">
        <tr>
          <td>
            <div style="font-weight:bold; color:{accent}; font-family:'Montserrat', Arial, sans-serif; font-size:14px; line-height:1.4;">
              {title}
            </div>
          </td>
        </tr>

        <tr>
          <td style="padding-top:5px; color:{text_main}; font-family:'Montserrat', Arial, sans-serif; font-size:14px; line-height:1.4;">
            <a href="{link}" target="_blank" style="color:#000000; text-decoration:underline;">
              Watch performance →
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
"""

    html += f"""
  <!-- SHARE / SIGNUP -->
  <tr>
    <td class="espacamento-lateral" style="padding:0 32px 25px; padding-left:32px; padding-right:32px;">
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="left" border="0" style="border-collapse:separate; background:#f7f7f5;">
        <tr>
          <td style="padding:24px 24px 25px; font-family:'Montserrat', Arial, sans-serif; color:#000000;">
            <div style="font-weight:bold; font-size:14px; line-height:1.4; padding-bottom:8px;">
              Know someone who might enjoy this?
            </div>
            <div style="font-size:13px; line-height:1.5; padding-bottom:14px;">
              Forward Motif to them. If you found this newsletter through someone else, you can join us here.
            </div>
            <a href="https://motifnewsletter.com" target="_blank" style="color:#000000; text-decoration:underline; font-size:13px; line-height:1.5;">
              Subscribe to Motif →
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td class="espacamento-lateral" style="padding:15px 32px 30px;">
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" align="left" border="0" style="border-top:2px solid #000000; padding-top:20px;">
        <tr>
          <td style="font-family:'Montserrat', Arial, sans-serif; font-size:12px; line-height:1.5; color:{text_muted};">
            You received this email because you subscribe to the Motif Newsletter.<br>
            Good Music for Good People.
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
