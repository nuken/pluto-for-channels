# Pluto for Channels

Current version: **1.25**

# About

This takes Pluto Live TV Channels and generates an M3U playlist and EPG XMLTV file. Forked from jgomez177/pluto-for-channels. Support his work below.

If you like this and other linear containers for Channels that I have created, please consider supporting my work.

[![](https://pics.paypal.com/00/s/MDY0MzZhODAtNGI0MC00ZmU5LWI3ODYtZTY5YTcxOTNlMjRm/file.PNG)](https://www.paypal.com/donate/?hosted_button_id=BBUTPEU8DUZ6J)

Or Even Better support the Girl Scouts with the purchase of cookies for the 2025 campaign:

Site 1
[<img src="https://townsquare.media/site/191/files/2024/01/attachment-cookie.jpg" width=400/>](https://digitalcookie.girlscouts.org/scout/charlotte816794)

Site 2
[<img src="https://townsquare.media/site/191/files/2024/01/attachment-cookie.jpg" width=400/>](https://digitalcookie.girlscouts.org/scout/mckenna899691)

# Changes

 - Version 1.25:
      - Now runs the entire process of creating the guide files once, immediately when it starts up. The background scheduler then takes over for all future updates.
      - Added rotating User-Agent strings from a list of common browser agents to make the script appear more like a regular user and reduce the risk of being blocked by Pluto TV's servers.
      - The application no longer holds the entire multi-megabyte EPG file in memory while building it. Instead, it processes the guide data and writes it directly to the .xml file piece by piece.
      - Instead of requesting guide data from the Pluto TV server one chunk at a time, the script now requests up to 10 chunks simultaneously.
 - Version 1.24:
      - Internal, not released.
 - Version 1.23:
      - Internal, not released. 
 - Version 1.22:
      - Internal, not released.
  - Version 1.21:
      - Added support for username and password authentication.
      - Added Pluto Germany.
  - Version 1.20:
      - additional error handling and thread monitoring.
  - Version 1.18:
      - Added additional error handling.
  - Version 1.17:
      - Fixed EPG data to verify Live programming.
  - Version 1.16:
      - Added Fix for CNN Headlines.
  - Version 1.15:
      - Adding ALL option that displays a single playlist/EPG for all selected countries in the container.
  - Version 1.14:
      - Remove control characters from station API summary string leaving other Unicode characters for tvc-guide-description in playlist
  - Version 1.13:
      - Merged optimizations offered up by **stewartcampbell** (Appreciate the support)
          - Remove EPG data when no longer required
          - Move EPG data retrieval logging line so that the correct start time is shown
          - Remove a redundant XML file read
          - Use Alpine Python image
          - Use pip instead of pip3 (alias exists in image)
          - Add --no-cache-dir flag to pip install
          - Add --disable-pip-version-check flag to pip install
          - Add --no-compile flag to pip install
          - Remove redundant $PATH code
          - Reorder commands for optimal layer caching
      - Added support for France
  - Version 1.12:
      - Changed HLS Stitcher to version 1 until “Playlist had no segments” issues can be resolved in version 2
  - Version 1.11:
      - Modified options for playlist to include a compatibility URL parameter.
      - Illegal character XML handling has been added.
  - Version 1.10:
      - Added tvc-guide-description to playlist
  - Version 1.09:
      - Added group-title to playlist

# Running
```
docker run -d --restart unless-stopped --network=host -e PLUTO_PORT=[your_port_number_here] -e PLUTO_USERNAME='your_username' -e PLUTO_PASSWORD='your_password' --name pluto-for-channels rcvaughn2/pluto-for-channels:main
```

or

```
docker run -d --restart unless-stopped -p [your_port_number_here]:7777 -e PLUTO_USERNAME='your_username' -e PLUTO_PASSWORD='your_password' --name  pluto-for-channels rcvaughn2/pluto-for-channels:main
```

You can retrieve the playlist and EPG via the status page.

```
[http://127.0.0.1](http://127.0.0.1):[your_port_number_here]
```

## Environement Variables

| Environment Variable | Description | Default |
|---|---|---|
| PLUTO\_PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |
| PLUTO\_USERNAME | Your Pluto TV username. | |
| PLUTO\_PASSWORD | Your Pluto TV password. | |
| PLUTO\_CODE | What country streams will be hosted. <br>Multiple can be hosted using comma separation\<p\>\<p\>ALLOWED\_COUNTRY\_CODES:<br>**us\_east** - United States East Coast,<br>**us\_west** - United States West Coast,<br>**local** - Local IP address Geolocation,<br>**ca** - Canada,<br>**uk** - United Kingdom, <br>**fr** - France, <br>**de** - Germany, | local,us\_west,us\_east,ca,uk |

## Additional URL Parameters

| Parameter | Description |
|---|---|
| channel\_id\_format | default channel-id is set as "pluto-{slug}".<br>**"id"** will change channel-id to "pluto-{id}".<br>**"slug\_only"** will change channel-id to "{slug}". |
