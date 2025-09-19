import uuid, requests, json, pytz, gzip, re, random
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from gevent.pool import Pool

class Client:
    def __init__(self, username=None, password=None):
        self.session = requests.Session()
        self.sessionAt = {}
        self.response_list = {}
        self.epg_data = {}
        self.device = None
        self.all_channels = {}
        self.username = username
        self.password = password
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        ]
        self.load_device()
        self.x_forward = {"local": {"X-Forwarded-For":""},
                          "uk": {"X-Forwarded-For":"178.238.11.6"},
                          "ca": {"X-Forwarded-For":"192.206.151.131"},
                          "fr": {"X-Forwarded-For":"193.169.64.141"},
                          "de": {"X-Forwarded-For":"81.173.176.155"},
                          "us_east": {"X-Forwarded-For":"108.82.206.181"},
                          "us_west": {"X-Forwarded-For":"76.81.9.69"},}

    def load_device(self):
        if self.device is None:
            self.device = uuid.uuid1()
        return(self.device)

    def resp_data(self, country_code):
        desired_timezone = pytz.timezone('UTC')
        current_date = datetime.now(desired_timezone)
        if (self.response_list.get(country_code) is not None) and (current_date - self.sessionAt.get(country_code, datetime.now())) < timedelta(hours=4):
            return self.response_list[country_code], None

        boot_headers = {
            'authority': 'boot.pluto.tv', 'accept': '*/*', 'accept-language': 'en-US,en;q=0.9', 'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/', 'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Linux"', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site', 'user-agent': random.choice(self.user_agents),
        }
        boot_params = {
            'appName': 'web', 'appVersion': '8.0.0-111b2b9dc00bd0bea9030b30662159ed9e7c8bc6', 'deviceVersion': '122.0.0',
            'deviceModel': 'web', 'deviceMake': 'chrome', 'deviceType': 'web', 'clientID': 'c63f9fbf-47f5-40dc-941c-5628558aec87',
            'clientModelNumber': '1.0.0', 'serverSideAds': 'false', 'drmCapabilities': 'widevine:L3', 'blockingMode': '',
            'notificationVersion': '1', 'appLaunchCount': '', 'lastAppLaunchDate': '',
        }
        if self.username and self.password:
            boot_params['username'] = self.username
            boot_params['password'] = self.password

        if country_code in self.x_forward:
            boot_headers.update(self.x_forward[country_code])

        try:
            response = self.session.get('https://boot.pluto.tv/v4/start', headers=boot_headers, params=boot_params)
            response.raise_for_status()
            resp = response.json()
            self.response_list[country_code] = resp
            self.sessionAt[country_code] = current_date
            print(f"New token for {country_code} generated at {current_date.strftime('%Y-%m-%d %H:%M:%S %z')}")
            return resp, None
        except requests.exceptions.RequestException as e:
            print(f"HTTP failure for {country_code}: {e}")
            return None, str(e)

    def channels(self, country_code):
        if country_code not in self.all_channels:
            resp, error = self.resp_data(country_code)
            if error: return None, error
            token = resp.get('sessionToken')
            if not token: return None, "No session token found"

            headers = {'authorization': f'Bearer {token}'}
            if country_code in self.x_forward:
                headers.update(self.x_forward[country_code])
            
            try:
                # Fetch channels
                channels_url = "https://service-channels.clusters.pluto.tv/v2/guide/channels"
                params = {'limit': '1000', 'sort': 'number:asc'}
                response = self.session.get(channels_url, headers=headers, params=params)
                response.raise_for_status()
                channel_list = response.json().get("data", [])

                # Fetch categories
                categories_url = "https://service-channels.clusters.pluto.tv/v2/guide/categories"
                response = self.session.get(categories_url, headers=headers, params={'limit': '1000'})
                response.raise_for_status()
                categories_data = response.json().get("data", [])
                
                categories_map = {chan_id: cat['name'] for cat in categories_data for chan_id in cat.get('channelIDs', [])}
                
                stations = []
                existing_numbers = set()
                for elem in channel_list:
                    number = elem.get('number')
                    while number in existing_numbers:
                        number += 1
                    existing_numbers.add(number)
                    
                    stations.append({
                        'id': elem.get('id'), 'name': elem.get('name'), 'slug': elem.get('slug'),
                        'tmsid': elem.get('tmsid'), 'summary': elem.get('summary'),
                        'group': categories_map.get(elem.get('id')), 'country_code': country_code,
                        'number': number,
                        'logo': next((img['url'] for img in elem.get('images', []) if img.get('type') == 'colorLogoPNG'), None)
                    })
                
                self.all_channels[country_code] = sorted(stations, key=lambda x: x["number"])
            except requests.exceptions.RequestException as e:
                return None, str(e)
        
        return self.all_channels[country_code], None

    def channels_all(self):
        all_channel_list = [chan for country_chans in self.all_channels.values() for chan in country_chans]
        
        seen_ids = set()
        unique_channels = [d for d in all_channel_list if d['id'] not in seen_ids and not seen_ids.add(d['id'])]

        country_offsets = {'ca': 6000, 'uk': 7000, 'fr': 8000, 'de': 9000}
        seen_numbers = set()
        for elem in unique_channels:
            number = elem.get('number', 0)
            offset = country_offsets.get(elem.get('country_code', '').lower(), 0)
            if number < offset:
                number += offset
            while number in seen_numbers:
                number += 1
            seen_numbers.add(number)
            elem['number'] = number
            
        return sorted(unique_channels, key=lambda x: x['number']), None

    def strip_illegal_characters(self, xml_string):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml_string or '')

    def _fetch_epg_data(self, url, params, headers):
        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching EPG data for params {params.get('channelIds', '')}: {e}")
            return None

    def update_epg(self, country_code, range_count=3):
        resp, error = self.resp_data(country_code)
        if error: return error
        token = resp.get('sessionToken')
        if not token: return "No session token for EPG update"

        station_list, error = self.channels(country_code)
        if error: return error
        
        url = "https://service-channels.clusters.pluto.tv/v2/guide/timelines"
        headers = {'authorization': f'Bearer {token}'}
        if country_code in self.x_forward:
            headers.update(self.x_forward[country_code])

        id_groups = [station_list[i:i + 100] for i in range(0, len(station_list), 100)]
        pool = Pool(10)
        country_data = []
        
        start_datetime = datetime.now(pytz.utc)
        for i in range(range_count):
            current_start_time = (start_datetime + timedelta(hours=i * 12)).strftime("%Y-%m-%dT%H:00:00.000Z")
            print(f'Retrieving {country_code} EPG data for {current_start_time}')
            
            jobs = [pool.spawn(self._fetch_epg_data, url, {
                'start': current_start_time, 'duration': '720',
                'channelIds': ','.join(d['id'] for d in group)
            }, headers) for group in id_groups]
            
            for job in jobs:
                if result := job.get():
                    country_data.append(result)

        self.epg_data[country_code] = country_data
        return None

    def _generate_programme_elements(self, resp):
        for entry in resp.get("data", []):
            for timeline in entry.get("timelines", []):
                try:
                    programme = ET.Element("programme", attrib={
                        "channel": entry["channelId"],
                        "start": datetime.strptime(timeline["start"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y%m%d%H%M%S %z"),
                        "stop": datetime.strptime(timeline["stop"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y%m%d%H%M%S %z")
                    })
                    ET.SubElement(programme, "title").text = self.strip_illegal_characters(timeline.get("title"))
                    if timeline.get("episode"):
                        ep = timeline["episode"]
                        ET.SubElement(programme, "desc").text = self.strip_illegal_characters(ep.get("description"))
                        if "season" in ep and "number" in ep:
                            ET.SubElement(programme, "episode-num", system="onscreen").text = f'S{ep["season"]:02d}E{ep["number"]:02d}'
                        if ep.get("series", {}).get("tile", {}).get("path"):
                             ET.SubElement(programme, "icon", src=ep["series"]["tile"]["path"])
                    yield programme
                except (KeyError, TypeError) as e:
                    # Skip malformed timeline entries
                    print(f"Skipping malformed EPG entry: {timeline.get('title', 'N/A')}, Error: {e}")
                    continue

    def create_xml_file(self, country_code):
        is_list = isinstance(country_code, list)
        station_list, error = self.channels_all() if is_list else self.channels(country_code)
        if error: return error

        xml_file_path = "epg-all.xml" if is_list else f"epg-{country_code}.xml"
        program_data = []
        if is_list:
            for code in country_code:
                program_data.extend(self.epg_data.get(code, []))
        else:
            program_data = self.epg_data.get(country_code, [])

        with open(xml_file_path, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(b'<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
            f.write(b'<tv generator-info-name="pluto-for-channels">\n')

            for station in station_list:
                channel = ET.Element("channel", id=station["id"])
                ET.SubElement(channel, "display-name").text = self.strip_illegal_characters(station["name"])
                if station.get("logo"):
                    ET.SubElement(channel, "icon", src=station["logo"])
                f.write(ET.tostring(channel, encoding='utf-8') + b'\n')

            for resp in program_data:
                for programme_element in self._generate_programme_elements(resp):
                    f.write(ET.tostring(programme_element, encoding='utf-8') + b'\n')
            
            f.write(b'</tv>\n')
        
        print(f"Successfully created {xml_file_path}")
        with open(xml_file_path, 'rb') as f_in, gzip.open(f"{xml_file_path}.gz", 'wb') as f_out:
            f_out.writelines(f_in)
        
        return None

    def clear_epg_data(self):
        self.epg_data = {}
