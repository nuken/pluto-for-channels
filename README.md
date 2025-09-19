# Pluto for Channels

Test Version (Subject to breaking)


# Running

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
