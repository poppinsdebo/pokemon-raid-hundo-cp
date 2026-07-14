# pokemon-raid-hundo-cp

A weekly-refreshed lookup table of 100% IV ("hundo") CP values for every
Pokemon species/form, at the CP levels raids catch at (20 normal, 25
weather-boosted). Built for a Siri Shortcut that looks up a dictated
species name and returns its hundo CP.

## Why this works without a live API

A raid boss's hundo CP only depends on its base stats and catch level, not
on the specific raid instance. Base stats are stable (they only change on
rare balance updates), so this can be precomputed instead of fetched live.

## Data source

[`scripts/generate_data.py`](scripts/generate_data.py) pulls Niantic's
GAME_MASTER file (mirrored by [PokeMiners](https://github.com/PokeMiners/game_masters))
and computes CP directly from the base stats and CP multiplier table
embedded in that same file — no hardcoded constants that can drift.

## Output

[`data/hundo_cp.json`](data/hundo_cp.json), keyed by species (e.g.
`PIKACHU`) or species_form for Pokemon with distinct alternate-form stats
(e.g. `RAICHU_ALOLA`, `GIRATINA_ORIGIN`). Cosmetic costumes are collapsed
into the base entry since they share identical stats.

```json
"MEWTWO": {
  "base_stats": { "attack": 300, "defense": 182, "stamina": 214 },
  "hundo_cp": { "level20": 2387, "level25": 2984 }
}
```

## Refresh schedule

[`.github/workflows/update-data.yml`](.github/workflows/update-data.yml)
runs every Monday 09:00 UTC (and on manual dispatch), regenerates the data,
and commits it if changed.

## Using it from a Siri Shortcut

Fetch the raw file and look up a dictionary key:

```
https://raw.githubusercontent.com/poppinsdebo/pokemon-raid-hundo-cp/main/data/hundo_cp.json
```

In Shortcuts: **Get Contents of URL** → **Get Dictionary Value** for `pokemon`
→ **Get Dictionary Value** for the uppercased, underscore-joined species
name dictated by Siri (e.g. "raichu alola" → `RAICHU_ALOLA`) → **Get
Dictionary Value** for `hundo_cp` → `level20`/`level25`.
