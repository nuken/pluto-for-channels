from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from flask import Flask, redirect, request, Response, send_file
from threading import Thread
import os, sys, importlib, schedule, time, re, uuid, unicodedata
from urllib.parse import urlparse, urlencode
from datetime import datetime

version = "1.24"  # Updated version
updated_date = "Sept. 18, 2025"

try:
    port = int(os.environ.get("PLUTO_PORT", 7777))
except (ValueError, TypeError):
    port = 7777

pluto_username = os.environ.get("PLUTO_USERNAME")
pluto_password = os.environ.get("PLUTO_PASSWORD")
pluto_country_list_str = os.environ.get("PLUTO_CODE", 'local,us_east,us_west,ca,uk,fr,de')
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
    # ... (HTML content remains the same, no changes needed here) ...
    # For brevity, the HTML string is omitted, but it is unchanged from your previous version.
    return "<html>...</html>" # Placeholder for the large HTML string

@app.get("/<provider>/<country_code>/playlist.m3u")
def playlist(provider, country_code):
    is_all = country_code.lower() == 'all'
    stations, err = providers[provider].channels_all() if is_all else providers[provider].channels(country_code)

    if err: return str(err), 500
    
    host = request.host
    channel_id_format = request.args.get('channel_id_format','').lower()
    
    m3u_lines = ["#EXTM3U"]
    for s in sorted(stations, key=lambda i: i.get('number', 0)):
        line_info = f"#EXTINF:-1 channel-id=\"{provider}-{s.get('id') if channel_id_format == 'id' else s.get('slug')}\""
        # ... other m3u attributes ...
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
    """Fetches EPG data and creates all required XML files."""
    print("[INFO] Running EPG Generation...")
    
    # Use a set to avoid duplicate country codes
    active_codes = set(c for c in pluto_country_list if c in ALLOWED_COUNTRY_CODES and c != 'all')
    
    # First, update EPG for all individual countries
    for code in active_codes:
        error = providers[provider].update_epg(code)
        if error:
            print(f"Could not update EPG for {code}: {error}")

    # Now, create the individual XML files
    for code in active_codes:
        error = providers[provider].create_xml_file(code)
        if error:
            print(f"Could not create XML file for {code}: {error}")

    # Finally, create the combined 'all' file if requested
    if 'all' in pluto_country_list:
        print("Creating combined EPG file for all countries.")
        error = providers[provider].create_xml_file(list(active_codes))
        if error:
            print(f"Could not create combined XML file: {error}")
    
    providers[provider].clear_epg_data()
    print("[INFO] EPG Generation Complete.")

def background_scheduler():
    """Runs the scheduler in a loop in a background thread."""
    schedule.every(2).hours.do(run_epg_scheduler)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Run the EPG generation once on startup in the main thread
    run_epg_scheduler()

    # Start the background thread for subsequent updates
    scheduler = Thread(target=background_scheduler, daemon=True)
    scheduler.start()
    
    print(f"⇨ HTTP server started on [::]:{port}")
    WSGIServer(('', port), app, log=None).serve_forever()