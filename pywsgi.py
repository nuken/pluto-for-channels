from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from flask import Flask, redirect, request, Response, send_file
from threading import Thread
import os, sys, importlib, schedule, time, re, uuid, unicodedata
from urllib.parse import urlparse, urlencode
from datetime import datetime

version = "1.26"  # Updated version
updated_date = "Sept. 19, 2025"

try:
    port = int(os.environ.get("PLUTO_PORT", 7777))
except (ValueError, TypeError):
    port = 7777

pluto_username = os.environ.get("PLUTO_USERNAME")
pluto_password = os.environ.get("PLUTO_PASSWORD")
pluto_country_list_str = os.environ.get("PLUTO_CODE", 'local,us_east,us_west,ca,uk,fr,de,all')
pluto_country_list = [code.strip() for code in pluto_country_list_str.split(',')]

ALLOWED_COUNTRY_CODES = ['local', 'us_east', 'us_west', 'ca', 'uk', 'fr', 'de', 'all']
app = Flask(__name__)
provider = "pluto"
providers = {
    provider: importlib.import_module(provider).Client(pluto_username, pluto_password),
}

def remove_non_printable(s):
    return ''.join(c for c in s if unicodedata.category(c)[0] != 'C')

@app.route("/")
def index():
    host = request.host
    html_content = f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{provider.capitalize()} Playlist</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css"><style>.url-container{{display:flex;align-items:center;margin-bottom:10px}}.url-container a{{flex-grow:1;margin-right:10px}}</style></head><body><section class="section"><div class="container"><h1 class="title">{provider.capitalize()} Playlist <span class="tag">v{version}</span></h1><p class="subtitle">Last Updated: {updated_date}</p>'
    
    if all(item in ALLOWED_COUNTRY_CODES for item in pluto_country_list):
        if 'all' in pluto_country_list:
            html_content += '<div class="box"><h2 class="title is-4">All Channels</h2>'
            pl = f"http://{host}/{provider}/all/playlist.m3u"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
            html_content += '</div>'
            html_content += '<div class="box"><h2 class="title is-4">All EPG</h2>'
            pl = f"http://{host}/{provider}/epg/all/epg-all.xml"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
            pl_gz = f"http://{host}/{provider}/epg/all/epg-all.xml.gz"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl_gz}\' target="_blank" rel="noopener noreferrer">{pl_gz}</a><button class="button is-info" onclick="copyToClipboard(\'{pl_gz}\')">Copy</button></div>'
            html_content += '</div>'

        for code in pluto_country_list:
            if code != 'all':
                html_content += f'<div class="box"><h2 class="title is-4">{code.upper()} Channels</h2>'
                pl = f"http://{host}/{provider}/{code}/playlist.m3u"
                html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
                html_content += '</div>'
                html_content += f'<div class="box"><h2 class="title is-4">{code.upper()} EPG</h2>'
                pl = f"http://{host}/{provider}/epg/{code}/epg-{code}.xml"
                html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
                pl_gz = f"http://{host}/{provider}/epg/{code}/epg-{code}.xml.gz"
                html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl_gz}\' target="_blank" rel="noopener noreferrer">{pl_gz}</a><button class="button is-info" onclick="copyToClipboard(\'{pl_gz}\')">Copy</button></div>'
                html_content += '</div>'
    else:
        html_content += f"<p>Invalid country code found in environment variables.</p>"

    html_content += '<script>function copyToClipboard(text){navigator.clipboard.writeText(text);}</script></div></section></body></html>'
    return html_content

@app.get("/<provider>/<country_code>/playlist.m3u")
def playlist(provider, country_code):
    is_all = country_code.lower() == 'all'
    stations, err = providers[provider].channels_all() if is_all else providers[provider].channels(country_code)

    if err: return str(err), 500
    
    host = request.host
    channel_id_format = request.args.get('channel_id_format','').lower()
    
    m3u_lines = ["#EXTM3U"]
    for s in sorted(stations, key=lambda i: i.get('number', 0)):
        if channel_id_format == 'id':
            chan_id_str = f"{provider}-{s.get('id')}"
        elif channel_id_format == 'slug_only':
            chan_id_str = s.get('slug')
        else:
            chan_id_str = f"{provider}-{s.get('slug')}"

        line_info = f"#EXTINF:-1 channel-id=\"{chan_id_str}\" tvg-id=\"{s.get('id', '')}\" tvg-chno=\"{s.get('number', '')}\" group-title=\"{s.get('group', '')}\" tvg-logo=\"{s.get('logo', '')}\""
        m3u_lines.append(f"{line_info},{s.get('name', '')}")
        m3u_lines.append(f"http://{host}/{provider}/{country_code}/watch/{s.get('id')}")
    
    return Response("\n".join(m3u_lines), content_type='audio/x-mpegurl')

@app.route("/<provider>/<country_code>/watch/<id>")
def watch(provider, country_code, id):
    resp, error = providers[provider].resp_data(country_code)
    if error: return str(error), 500
    
    params = {
        'advertisingId': '', 'appName': 'web', 'appVersion': 'unknown', 'deviceId': providers[provider].load_device(),
        'deviceMake': 'Chrome', 'deviceModel': 'web', 'deviceType': 'web', 'sid': uuid.uuid4(),
        'jwt': resp.get('sessionToken',''), 'masterJWTPassthrough': 'true'
    }
    video_url = f"https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv/stitch/hls/channel/{id}/master.m3u8?{urlencode(params)}"
    return redirect(video_url)

@app.get("/<provider>/epg/<country_code>/<filename>")
def epg_xml(provider, country_code, filename):
    if country_code not in ALLOWED_COUNTRY_CODES or not re.match(r'epg-[\w-]+\.xml(\.gz)?', filename):
        return "Invalid request", 400

    if not os.path.exists(filename):
        return "EPG file not found. It may still be generating.", 404

    mimetype = 'application/gzip' if filename.endswith('.gz') else 'application/xml'
    return send_file(filename, as_attachment=filename.endswith('.gz'), mimetype=mimetype)

def run_epg_scheduler():
    print("[INFO] Running EPG Generation...")
    
    active_codes = set(c for c in pluto_country_list if c in ALLOWED_COUNTRY_CODES and c != 'all')
    
    for code in active_codes:
        if error := providers[provider].update_epg(code):
            print(f"Could not update EPG for {code}: {error}")

    for code in active_codes:
        if error := providers[provider].create_xml_file(code):
            print(f"Could not create XML file for {code}: {error}")

    if 'all' in pluto_country_list:
        print("Creating combined EPG file for all countries.")
        if error := providers[provider].create_xml_file(list(active_codes)):
            print(f"Could not create combined XML file: {error}")
    
    providers[provider].clear_epg_data()
    print("[INFO] EPG Generation Complete.")

def background_scheduler():
    schedule.every(2).hours.do(run_epg_scheduler)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    run_epg_scheduler()

    scheduler = Thread(target=background_scheduler, daemon=True)
    scheduler.start()
    
    print(f"⇨ HTTP server started on [::]:{port}")
    WSGIServer(('', port), app, log=None).serve_forever()
