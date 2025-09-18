import uuid, requests, json, pytz, gzip, re
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
            'authority': 'boot.pluto.tv',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            }

        boot_params = {
            'appName': 'web',
            'appVersion': '8.0.0-111b2b9dc00bd0bea9030b30662159ed9e7c8bc6',
            'deviceVersion': '122.0.0',
            'deviceModel': 'web',
            'deviceMake': 'chrome',
            'deviceType': 'web',
            'clientID': 'c63f9fbf-47f5-40dc-941c-5628558aec87',
            'clientModelNumber': '1.0.0',
            'serverSideAds': 'false',
            'drmCapabilities': 'widevine:L3',
            'blockingMode': '',
            'notificationVersion': '1',
            'appLaunchCount': '',
            'lastAppLaunchDate': '',
            }

        if self.username and self.password:
            boot_params['username'] = self.username
            boot_params['password'] = self.password

        if country_code in self.x_forward.keys():
            boot_headers.update(self.x_forward.get(country_code))

        try:
            response = self.session.get('https://boot.pluto.tv/v4/start', headers=boot_headers, params=boot_params)
        except Exception as e:
            return None, (f"Error Exception type: {type(e).__name__}")

        if (200 <= response.status_code <= 201):
            resp = response.json()
        else:
            print(f"HTTP failure {response.status_code}: {response.text}")
            return None, f"HTTP failure {response.status_code}: {response.text}"

        self.response_list.update({country_code: resp})
        self.sessionAt.update({country_code: current_date})
        print(f"New token for {country_code} generated at {(self.sessionAt.get(country_code)).strftime('%Y-%m-%d %H:%M.%S %z')}")

        return self.response_list.get(country_code), None

    def channels(self, country_code):
        if country_code == 'all':
            return(self.channels_all())

        resp, error = self.resp_data(country_code)
        if error: return None, error

        token = resp.get('sessionToken', None)
        if token is None: return None, error

        url = f"https://service-channels.clusters.pluto.tv/v2/guide/channels"

        headers = {
            'authority': 'service-channels.clusters.pluto.tv',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {token}',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/',
            }

        params = {
            'channelIds': '',
            'offset': '0',
            'limit': '1000',
            'sort': 'number:asc',
            }

        if country_code in self.x_forward.keys():
            headers.update(self.x_forward.get(country_code))

        try:
            response = self.session.get(url, params=params, headers=headers)
        except Exception as e:
            return None, (f"Error Exception type: {type(e).__name__}")

        if response.status_code != 200:
            return None, f"HTTP failure {response.status_code}: {response.text}"

        channel_list = response.json().get("data")

        category_url = f"https://service-channels.clusters.pluto.tv/v2/guide/categories"

        try:
            response = self.session.get(category_url, params=params, headers=headers)
        except Exception as e:
            return None, (f"Error Exception type: {type(e).__name__}")

        if response.status_code != 200:
            return None, f"HTTP failure {response.status_code}: {response.text}"

        categories_data = response.json().get("data")

        categories_list = {}
        for elem in categories_data:
            category = elem.get('name')
            channelIDs = elem.get('channelIDs')
            for channel in channelIDs:
                categories_list.update({channel: category})

        stations = []
        for elem in channel_list:
            entry = {'id': elem.get('id'),
                    'name': elem.get('name'),
                    'slug': elem.get('slug'),
                    'tmsid': elem.get('tmsid'),
                    'summary': elem.get('summary'),
                    'group': categories_list.get(elem.get('id')),
                    'country_code': country_code}
            number = elem.get('number')
            existing_numbers = {channel["number"] for channel in stations}
            while number in existing_numbers:
                number += 1
            color_logo_png = next((image["url"] for image in elem["images"] if image["type"] == "colorLogoPNG"), None)
            entry.update({'number': number, 'logo': color_logo_png})

            stations.append(entry)

        sorted_data = sorted(stations, key=lambda x: x["number"])
        self.all_channels.update({country_code: sorted_data})
        return(sorted_data, None)

    def channels_all(self):
        all_channel_list = []
        for key, val in self.all_channels.items():
            all_channel_list.extend(val)
        seen = set()
        filter_key = 'id'
        filtered_list = [d for d in all_channel_list if d[filter_key] not in seen and not seen.add(d[filter_key])]
        seen = set()
        for elem in filtered_list:
            number = elem.get('number')
            match elem.get('country_code').lower():
                case 'ca':
                    offset = 6000
                    if number < offset:
                        number += offset
                case 'uk':
                    offset = 7000
                    if number < offset:
                        number += offset
                case 'fr':
                    offset = 8000
                    if number < offset:
                        number += offset
                case 'de':
                    offset = 9000
                    if number < offset:
                        number += offset
            while number in seen:
                number += 1
            seen.add(number)
            if number != elem.get('number'):
                elem.update({'number': number})

        return(filtered_list, None)

    def strip_illegal_characters(self, xml_string):
        illegal_char_pattern = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
        clean_xml_string = illegal_char_pattern.sub('', xml_string)
        return clean_xml_string

    def _fetch_epg_data(self, url, params, headers):
        try:
            response = self.session.get(url, params=params, headers=headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching EPG data: {e}")
        return None

    def update_epg(self, country_code, range_count=3):
        resp, error = self.resp_data(country_code)
        if error: return None, error
        token = resp.get('sessionToken', None)
        if token is None: return None, error

        desired_timezone = pytz.timezone('UTC')
        start_datetime = datetime.now(desired_timezone)
        start_time = start_datetime.strftime("%Y-%m-%dT%H:00:00.000Z")

        url = "https://service-channels.clusters.pluto.tv/v2/guide/timelines"
        epg_headers = {
            'authority': 'service-channels.clusters.pluto.tv',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {token}',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/',
        }
        if country_code in self.x_forward.keys():
            epg_headers.update(self.x_forward.get(country_code))

        station_list, error = self.channels(country_code)
        if error: return None, error

        id_values = [d['id'] for d in station_list]
        group_size = 100
        grouped_id_values = [id_values[i:i + group_size] for i in range(0, len(id_values), group_size)]
        
        country_data = []
        pool = Pool(10) # Create a pool of 10 greenlets

        for i in range(range_count):
            current_start_time = (start_datetime + timedelta(hours=i*12)).strftime("%Y-%m-%dT%H:00:00.000Z")
            print(f'Retrieving {country_code} EPG data for {current_start_time}')

            jobs = []
            for group in grouped_id_values:
                params = {
                    'start': current_start_time,
                    'channelIds': ','.join(map(str, group)),
                    'duration': '720',
                }
                jobs.append(pool.spawn(self._fetch_epg_data, url, params.copy(), epg_headers))
            
            pool.join() # Wait for all jobs to complete

            for job in jobs:
                if job.value:
                    country_data.append(job.value)

        self.epg_data[country_code] = country_data
        return None

    def find_tuples_by_value(self, dictionary, target_value):
        result_list = []
        for key, values in dictionary.items():
            if target_value in values:
                result_list.extend(key)
        return result_list if result_list else [target_value]

    def read_epg_data(self, resp):
        seriesGenres = {
            ("Animated",): ["Family Animation", "Cartoons"],
            ("Educational",): ["Education & Guidance", "Instructional & Educational"],
            ("News",): ["News and Information", "General News", "News + Opinion", "General News"],
            ("History",): ["History & Social Studies"],
            ("Politics",): ["Politics"],
            ("Action",):
                [
                  "Action & Adventure",
                  "Action Classics",
                  "Martial Arts",
                  "Crime Action",
                  "Family Adventures",
                  "Action Sci-Fi & Fantasy",
                  "Action Thrillers",
                  "African-American Action",
                ],
            ("Adventure",): ["Action & Adventure", "Adventures", "Sci-Fi Adventure"],
            ("Reality",):
                [
                  "Reality",
                  "Reality Drama",
                  "Courtroom Reality",
                  "Occupational Reality",
                  "Celebrity Reality",
                ],
            ("Documentary",):
                [
                  "Documentaries",
                  "Social & Cultural Documentaries",
                  "Science and Nature Documentaries",
                  "Miscellaneous Documentaries",
                  "Crime Documentaries",
                  "Travel & Adventure Documentaries",
                  "Sports Documentaries",
                  "Military Documentaries",
                  "Political Documentaries",
                  "Foreign Documentaries",
                  "Religion & Mythology Documentaries",
                  "Historical Documentaries",
                  "Biographical Documentaries",
                  "Faith & Spirituality Documentaries",
                ],
            ("Biography",): ["Biographical Documentaries", "Inspirational Biographies"],
            ("Science Fiction",): ["Sci-Fi Thrillers", "Sci-Fi Adventure", "Action Sci-Fi & Fantasy"],
            ("Thriller",): ["Sci-Fi Thrillers", "Thrillers", "Crime Thrillers"],
            ("Biography",): ["Biographical Documentaries", "Inspirational Biographies"],
            ("Talk",): ["Talk & Variety", "Talk Show"],
            ("Variety",): ["Sketch Comedies"],
            ("Home Improvement",): ["Art & Design", "DIY & How To", "Home Improvement"],
            ("House/garden",): ["Home & Garden"],
            ("Cooking",): ["Cooking Instruction", "Food & Wine", "Food Stories"],
            ("Travel",): ["Travel & Adventure Documentaries", "Travel"],
            ("Western",): ["Westerns", "Classic Westerns"],
            ("LGBTQ",): ["Gay & Lesbian", "Gay & Lesbian Dramas", "Gay"],
            ("Game show",): ["Game Show"],
            ("Military",): ["Classic War Stories"],
            ("Comedy",):
                [
                  "Cult Comedies",
                  "Spoofs and Satire",
                  "Slapstick",
                  "Classic Comedies",
                  "Stand-Up",
                  "Sports Comedies",
                  "African-American Comedies",
                  "Showbiz Comedies",
                  "Sketch Comedies",
                  "Teen Comedies",
                  "Latino Comedies",
                  "Family Comedies",
                ],
            ("Crime",): ["Crime Action", "Crime Drama", "Crime Documentaries"],
            ("Sports",): ["Sports","Sports & Sports Highlights","Sports Documentaries", "Poker & Gambling"],
            ("Poker & Gambling",): ["Poker & Gambling"],
            ("Crime drama",): ["Crime Drama"],
            ("Drama",):
                [
                  "Classic Dramas",
                  "Family Drama",
                  "Indie Drama",
                  "Romantic Drama",
                  "Crime Drama",
                ],
            ("Children",): ["Kids", "Children & Family", "Kids' TV", "Cartoons", "Animals", "Family Animation", "Ages 2-4", "Ages 11-12",],
            ("Animated",): ["Family Animation", "Cartoons"]
            }

        for entry in resp.get("data", []):
            for timeline in entry.get("timelines", []):
                programme = ET.Element("programme", attrib={"channel": entry["channelId"],
                                                                 "start": datetime.strptime(timeline["start"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y%m%d%H%M%S %z"),
                                                                 "stop": datetime.strptime(timeline["stop"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y%m%d%H%M%S %z")})
                title = ET.SubElement(programme, "title")
                title.text = self.strip_illegal_characters(timeline["title"])
                if timeline.get("episode", {}).get("series", {}).get("type", "") == "live":
                    if timeline["episode"]["clip"]["originalReleaseDate"] == timeline["start"]:
                        ET.SubElement(programme, "live")
                if timeline.get("episode", {}).get("season"):
                    episode_num_onscreen = ET.SubElement(programme, "episode-num", attrib={"system": "onscreen"})
                    episode_num_onscreen.text = f'S{timeline["episode"]["season"]:02d}E{timeline["episode"]["number"]:02d}'
                
                desc = ET.SubElement(programme, "desc")
                desc.text = self.strip_illegal_characters(timeline.get("episode", {}).get("description", "")).replace('&quot;', '"')
                
                if timeline.get("episode", {}).get("series", {}).get("tile", {}).get("path"):
                    ET.SubElement(programme, "icon", attrib={"src": timeline["episode"]["series"]["tile"]["path"]})
                
                date = ET.SubElement(programme, "date")
                date.text = datetime.strptime(timeline.get("episode", {}).get("clip", {}).get("originalReleaseDate"), "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y%m%d")

                if timeline.get("episode", {}).get("series", {}).get("_id"):
                    series_id_pluto = ET.SubElement(programme, "series-id", attrib={"system": "pluto"})
                    series_id_pluto.text = timeline["episode"]["series"]["_id"]

                if timeline["title"].lower() != timeline.get("episode", {}).get("name", "").lower():
                    sub_title = ET.SubElement(programme, "sub-title")
                    sub_title.text = self.strip_illegal_characters(timeline.get("episode", {}).get("name", ""))

                categories = []
                if timeline.get("episode", {}).get("genre"):
                    categories.extend(self.find_tuples_by_value(seriesGenres, timeline["episode"]["genre"]))
                if timeline.get("episode", {}).get("subGenre"):
                    categories.extend(self.find_tuples_by_value(seriesGenres, timeline["episode"]["subGenre"]))

                unique_list = sorted(list(set(categories)))
                for category in unique_list:
                    category_elem = ET.SubElement(programme, "category")
                    category_elem.text = category
                
                yield programme

    def get_all_epg_data(self, country_codes):
        all_epg_data = []
        channelIds_seen = set()

        for country in country_codes:
            self.update_epg(country)
            for epg_list in self.epg_data.get(country, []):
                for entry in epg_list.get('data', []):
                    channelId = entry.get('channelId')
                    if channelId not in channelIds_seen:
                        all_epg_data.append(entry)
                        channelIds_seen.add(channelId)
        
        return [{'data': all_epg_data}]

    def create_xml_file(self, country_code):
        if isinstance(country_code, str):
            error_code = self.update_epg(country_code)
            if error_code: return error_code
            station_list, error = self.channels(country_code)
            if error: return None, error
            xml_file_path = f"epg-{country_code}.xml"
            program_data = self.epg_data.get(country_code, [])

        elif isinstance(country_code, list):
            xml_file_path = "epg-all.xml"
            station_list, error = self.channels_all()
            if error: return None, error
            program_data = self.get_all_epg_data(country_code)
        else:
            print("The variable is neither a string nor a list.")
            return None

        compressed_file_path = f"{xml_file_path}.gz"

        with open(xml_file_path, "wb") as f:
            f.write(b'<?xml version=\'1.0\' encoding=\'utf-8\'?>\n')
            f.write(b'<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
            f.write(b'<tv generator-info-name="jgomez177">\n')

            for station in station_list:
                channel = ET.Element("channel", attrib={"id": station["id"]})
                display_name = ET.SubElement(channel, "display-name")
                display_name.text = self.strip_illegal_characters(station["name"])
                ET.SubElement(channel, "icon", attrib={"src": station["logo"]})
                f.write(ET.tostring(channel, encoding='utf-8'))
                f.write(b'\n')

            for elem in program_data:
                for programme_element in self.read_epg_data(elem):
                    f.write(ET.tostring(programme_element, encoding='utf-8'))
                    f.write(b'\n')
            
            f.write(b'</tv>\n')

        with open(xml_file_path, 'rb') as f_in, gzip.open(compressed_file_path, 'wb') as f_out:
            f_out.writelines(f_in)
        
        self.epg_data = {}
        return None