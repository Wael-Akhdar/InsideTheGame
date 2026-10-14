# Overlay JSON

The output a broadcaster or video app consumes: the whole match as timestamped cards. There is no video in this
repo, so the overlay is data only; a renderer places each card on screen.

```bash
python -m gamepulse.overlay --source sim --seed 42 --lang fr --out overlay.json   # sim | wyscout | sportec
curl "http://localhost:8000/api/overlay?source=wyscout&lang=es&mode=analyst"
```

Query/CLI options: `source`, `seed`, `league` (wyscout), `lang` (en/fr/es/ar), `mode` (casual/analyst),
`team` (favourite club id) and `player` (follow-a-player id) on the API.

```json
{ "schema": "gamepulse.overlay/1", "source": "...", "teams": {"RVR": "..."}, "score": {"RVR": 1, "NTH": 2},
  "overlays": [ { "id": 1, "t": 1201, "duration": 7.0, "at_minute": 20, "kind": "key_player",
                  "team": "NTH", "player": "NTH9", "headline": "...", "body": "...", "explanation": "...",
                  "evidence": [258, 259], "importance": 0.62, "lang": "en", "mode": "casual" } ] }
```

- `t`: match clock in seconds since kickoff (second half starts at 45:00 or later, like the event feed).
  A player adds its own kickoff offset and half-time gap.
- `evidence`: ids of the events that justify the card (every claim is traceable).
- Cards are sorted by `t`; same seed and settings give the same JSON.
- Real feeds are pseudonymised (players and clubs); simulator names are fictional.
