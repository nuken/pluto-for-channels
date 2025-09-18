from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from flask import Flask, redirect, request, Response, send_file
from threading import Thread
import os, sys, importlib, schedule, time, re, uuid, unicodedata
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
from datetime import datetime, timedelta

version = "1.23"  # Updated version
updated_date = "Sept. 18, 2025"

try:
    port = int(os.environ.get("PLUTO_PORT", 7777))
except:
    port = 7777

pluto_username = os.environ.get("PLUTO_USERNAME")
pluto_password = os.environ.get("PLUTO_PASSWORD")

pluto_country_list = os.environ.get("PLUTO_CODE")
if pluto_country_list:
   pluto_country_list = pluto_country_list.split(',')
else:
   pluto_country_list = ['local', 'us_east', 'us_west', 'ca', 'uk', 'fr', 'de']

ALLOWED_COUNTRY_CODES = ['local', 'us_east', 'us_west', 'ca', 'uk', 'fr', 'de', 'all']
app = Flask(__name__)
provider = "pluto"
providers = {
    provider: importlib.import_module(provider).Client(pluto_username, pluto_password),
}

def remove_non_printable(s):
    return ''.join([char for char in s if not unicodedata.category(char).startswith('C')])

url = f'<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{provider.capitalize()} Playlist</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css"><style>.url-container{{display:flex;align-items:center;margin-bottom:10px}}.url-container a{{flex-grow:1;margin-right:10px}}</style></head><body><section class="section"><div class="container"><h1 class="title">{provider.capitalize()} Playlist <span class="tag">v{version}</span></h1><p class="subtitle">Last Updated: {updated_date}</p>'

@app.route("/")
def index():
    host = request.host
    html_content = ""
    if all(item in ALLOWED_COUNTRY_CODES for item in pluto_country_list):
        html_content += '<div class="box"><h2 class="title is-4">All Channels</h2>'
        pl = f"http://{host}/{provider}/all/playlist.m3u"
        html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
        pl = f"http://{host}/{provider}/all/playlist.m3u?channel_id_format=id"
        html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
        pl = f"http://{host}/{provider}/all/playlist.m3u?channel_id_format=slug_only"
        html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div></div>'
        html_content += '<div class="box"><h2 class="title is-4">All EPG</h2>'
        pl = f"http://{host}/{provider}/epg/all/epg-all.xml"
        html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
        pl = f"http://{host}/{provider}/epg/all/epg-all.xml.gz"
        html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div></div>'

        for code in pluto_country_list:
            if code == 'all': continue
            html_content += f'<div class="box"><h2 class="title is-4">{code.upper()} Channels</h2>'
            pl = f"http://{host}/{provider}/{code}/playlist.m3u"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
            pl = f"http://{host}/{provider}/{code}/playlist.m3u?channel_id_format=id"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
            pl = f"http://{host}/{provider}/{code}/playlist.m3u?channel_id_format=slug_only"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div></div>'
            html_content += f'<div class="box"><h2 class="title is-4">{code.upper()} EPG</h2>'
            pl = f"http://{host}/{provider}/epg/{code}/epg-{code}.xml"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div>'
            pl = f"http://{host}/{provider}/epg/{code}/epg-{code}.xml.gz"
            html_content += f'<div class="url-container"><a class="button is-link is-light" href=\'{pl}\' target="_blank" rel="noopener noreferrer">{pl}</a><button class="button is-info" onclick="copyToClipboard(\'{pl}\')">Copy</button></div></div>'
    else:
        html_content += f"<li>INVALID COUNTRY CODE in \"{', '.join(pluto_country_list).upper()}\"</li>\n"
    html_content += '<script>function copyToClipboard(text){var dummy=document.createElement("textarea");document.body.appendChild(dummy);dummy.value=text;dummy.select();document.execCommand("copy");document.body.removeChild(dummy)}</script>'
    return f"{url}{html_content}</div></section></body></html>"

@app.route("/<country_code>/token")
def token(country_code):
    resp, error = providers[provider].resp_data(country_code)
    if error: return f"ERROR: {error}", 400
    return resp.get('sessionToken', '')

@app.route("/<provider>/<country_code>/channels")
def channels(provider, country_code):
    channels, error = providers[provider].channels(country_code)
    if error: return f"ERROR: {error}", 400
    return channels

@app.get("/<provider>/<country_code>/playlist.m3u")
def playlist(provider, country_code):
    if country_code.lower() == 'all':
        stations, err = providers[provider].channels_all()
    elif country_code.lower() in ALLOWED_COUNTRY_CODES:
        stations, err = providers[provider].channels(country_code)
    else:
        return "Invalid county code", 400

    if err: return err, 500
    
    host = request.host
    channel_id_format = request.args.get('channel_id_format','').lower()
    stations = sorted(stations, key = lambda i: i.get('number', 0))

    m3u = "#EXTM3U\r\n\r\n"
    for s in stations:
        if channel_id_format == 'id':
            m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('id')}\""
        elif channel_id_format == 'slug_only':
            m3u += f"#EXTINF:-1 channel-id=\"{s.get('slug')}\""
        else:
            m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('slug')}\""
        m3u += f" tvg-id=\"{s.get('id')}\" tvg-chno=\"{s.get('number', '')}\" group-title=\"{s.get('group', '')}\" tvg-logo=\"{s.get('logo', '')}\" tvg-name=\"{s.get('tmsid', '')}\" tvc-guide-title=\"{s.get('name', '')}\" tvc-guide-description=\"{remove_non_printable(s.get('summary', ''))}\",{s.get('name') or s.get('call_sign')}\n"
        m3u += f"http://{host}/{provider}/{country_code}/watch/{s.get('id')}\n\n"

    return Response(m3u, content_type='audio/x-mpegurl')

@app.route("/<provider>/<country_code>/watch/<id>")
def watch(provider, country_code, id):
    client_id = providers[provider].load_device()
    sid = uuid.uuid4()
    stitcher = "https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv"
    
    resp, error = providers[provider].resp_data(country_code)
    if error: return error, 500

    params = {
        'advertisingId': '', 'appName': 'web', 'appVersion': 'unknown', 'appStoreUrl': '', 'architecture': '', 'buildVersion': '',
        'clientTime': '0', 'deviceDNT': '0', 'deviceId': client_id, 'deviceMake': 'Chrome', 'deviceModel': 'web',
        'deviceType': 'web', 'deviceVersion': 'unknown', 'includeExtendedEvents': 'false', 'sid': sid, 'userId': '', 'serverSideAds': 'true',
        'jwt': resp.get('sessionToken',''), 'masterJWTPassthrough': 'true'
    }
    
    video_url = f"{stitcher}/stitch/hls/channel/{id}/master.m3u8?{urlencode(params)}"
    return redirect(video_url)

@app.get("/<provider>/epg/<country_code>/<filename>")
def epg_xml(provider, country_code, filename):
    ALLOWED_EPG_FILENAMES = {f'epg-{code}.xml' for code in ALLOWED_COUNTRY_CODES}
    ALLOWED_GZ_FILENAMES = {f'epg-{code}.xml.gz' for code in ALLOWED_COUNTRY_CODES}

    if country_code not in ALLOWED_COUNTRY_CODES:
        return "Invalid county code", 400
    if filename not in ALLOWED_EPG_FILENAMES and filename not in ALLOWED_GZ_FILENAMES:
        return "Invalid filename", 400

    file_path = f'{filename}'
    if not os.path.exists(file_path):
        return "XML file not found", 404

    mimetype = 'application/gzip' if filename.endswith('.gz') else 'text/xml'
    return send_file(file_path, as_attachment=filename.endswith('.gz'), download_name=file_path, mimetype=mimetype)

def epg_scheduler():
    print("[INFO] Running EPG Scheduler")
    active_codes = [code for code in pluto_country_list if code != 'all']
    for code in active_codes:
        error = providers[provider].create_xml_file(code)
        if error: print(f"Error creating EPG for {code}: {error}")
    
    if 'all' in pluto_country_list:
        error = providers[provider].create_xml_file(active_codes)
        if error: print(f"Error creating combined EPG: {error}")

    providers[provider].clear_epg_data()
    print("[INFO] EPG Scheduler Complete")

def scheduler_thread():
    epg_scheduler()
    schedule.every(2).hours.do(epg_scheduler)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=scheduler_thread, daemon=True).start()
    print(f"⇨ http server started on [::]:{port}")
    WSGIServer(('', port), app).serve_forever()