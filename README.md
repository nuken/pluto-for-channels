# Pluto for Channels

**Test Version 1.25 (Subject to breaking)**

**This version needs testers. I made a lot of changes that may or may not work under different setups. Your feedback is appreciated.**

## **Improvements**

### **1. Concurrent (Parallel) Guide Data Fetching**
* **The Change:** Instead of requesting guide data from the Pluto TV server one chunk at a time, the script now requests up to 10 chunks simultaneously.
* **The Improvement:** This is the most significant performance boost. It dramatically **reduces the time** it takes to download the electronic program guide (EPG) because the application is no longer sitting idle waiting for one request to finish before starting the next.

---
### **2. Streaming XML File Generation**
* **The Change:** The application no longer holds the entire multi-megabyte EPG file in memory while building it. Instead, it processes the guide data and writes it directly to the `.xml` file piece by piece.
* **The Improvement:** This massively **reduces the application's RAM usage**. It prevents the container from consuming excessive system resources and makes it much more stable, especially on systems with limited memory (like a Raspberry Pi).

---
### **3. EPG Generation on Startup**
* **The Change:** The application now runs the entire process of creating the guide files **once, immediately when it starts up**. The background scheduler then takes over for all future updates.
* **The Improvement:** It eliminates a race condition where the web server could start before the EPG files existed, ensuring the files are **always available** from the moment the container is running.



# Running
Use single quotes around the username and password to avoid conflicts.
```
docker run -d --restart unless-stopped --network=host -e PLUTO_PORT=[your_port_number_here] -e PLUTO_USERNAME='your_username' -e PLUTO_PASSWORD='your_password' --name pluto-for-channels rcvaughn2/pluto-for-channels:test
```

or

```
docker run -d --restart unless-stopped -p [your_port_number_here]:7777 -e PLUTO_USERNAME'[your_username' -e PLUTO_PASSWORD='your_password' --name  pluto-for-channels rcvaughn2/pluto-for-channels:test
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
