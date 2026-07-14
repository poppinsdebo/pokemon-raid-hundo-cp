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

There's also a top-level `lookup` dict that maps a normalized spoken phrase
(lowercase, alphanumeric-only — spaces/apostrophes/punctuation stripped) to
the matching `pokemon` key, e.g. `"raichualola"` and `"alolanraichu"` both
map to `"RAICHU_ALOLA"`. This exists so a Siri Shortcut can turn dictated
text straight into a dictionary key without doing fuzzy matching on-device
— [`scripts/generate_data.py`](scripts/generate_data.py) (`build_aliases`)
handles regional-form word order (Alolan/Galarian/Hisuian/Paldean can be said
before or after the species) and Siri-dictation-prone names (Mr. Mime,
Farfetch'd, Ho-Oh, Type: Null, etc.).

## Refresh schedule

[`.github/workflows/update-data.yml`](.github/workflows/update-data.yml)
runs every Monday 09:00 UTC (and on manual dispatch), regenerates the data,
and commits it if changed. Note: `generated_at` changes on every run, so it
commits weekly regardless of whether the underlying Pokemon data changed.

## Building the Siri Shortcut

Goal: say "Hey Siri, what's the hundo of Tyranitar" and hear "For Tyranitar,
Regular: 2191 CP and Weather Boosted: 2739 CP." One shortcut, no server.

### Option A: import the prebuilt shortcut

[`shortcuts/Hundo Lookup.shortcut`](shortcuts/Hundo%20Lookup.shortcut) is a
hand-assembled, **untested** starting point — Ask for Input → normalize →
fetch → look up → speak, matching Option B below minus the "not found"
guard. Transfer it to your phone (AirDrop, iCloud Drive, etc.), open it from
the Files app, and if prompted, enable *Settings → Shortcuts → Allow
Untrusted Shortcuts* first. If any action shows a red "missing variable"
indicator on import, tap it and reconnect using Option B as the reference
for what that field should point to.

<!-- TODO once confirmed working on-device: replace this note with exact
     install steps (transfer method, prompts you'll see, anything you had
     to fix). -->

### Option B: build it by hand

Raw data URL:

```
https://raw.githubusercontent.com/poppinsdebo/pokemon-raid-hundo-cp/main/data/hundo_cp.json
```

Create a new shortcut in the Shortcuts app with these actions, in order.
The **Get Dictionary Value** action reads as a sentence: **"Get [Value] for
[Key] in [Dictionary]."** Where a step's result needs to be referenced by
several later steps, add a **Set Variable** action right after it and give
it an explicit name — that's how you tell its output apart later, since
not every Shortcuts version lets you rename a magic variable inline.

1. **Text** — leave the field empty, then long-press it and choose
   **Ask Each Time**. This is the parameter Siri will fill with the
   dictated species name.
2. **Change Case** — Input: the Text from step 1. Case: **lowercase**.
3. **Replace Text** — tap the chevron/"Show More" at the bottom of the
   action card to reveal **Regular Expression**, and turn it on. Find
   `[^a-z0-9]`, Replace with nothing. Input: output of step 2. (Strips
   spaces, apostrophes, hyphens — mirrors the `lookup` table's
   normalization.) → **Set Variable**, name it `NormalizedName`.
4. **Get Contents of URL** — URL: the raw data URL above, Method: GET.
5. **Get Value for** `lookup` **in** *(the contents from step 4 — Shortcuts
   will auto-insert a "Get Dictionary from Input" action first; accept
   it)* → **Set Variable**, name it `LookupDict`.
6. **Get Value for** `NormalizedName` **in** `LookupDict`. This returns the
   canonical species key (e.g. `RAICHU_ALOLA`), or nothing if not found →
   **Set Variable**, name it `SpeciesKey`.
7. **If** — Input: `SpeciesKey`, Condition: **has any value**.
   - **Otherwise**: **Speak Text** "I couldn't find a hundo CP for that
     Pokemon." then **Stop Shortcut**.
8. Inside the **If** (true) branch:
   - **Get Value for** `pokemon` **in** *(contents from step 4)* →
     **Set Variable**, name it `PokemonDict`.
   - **Get Value for** `SpeciesKey` **in** `PokemonDict`. This is the
     `{base_stats, hundo_cp}` entry → **Set Variable**, name it `Entry`.
   - **Get Value for** `hundo_cp` **in** `Entry` → **Set Variable**, name
     it `HundoCP`.
   - **Get Value for** `level20` **in** `HundoCP` → **Set Variable**, name
     it `Regular`.
   - **Get Value for** `level25` **in** `HundoCP` → **Set Variable**, name
     it `Boosted`.
   - **Replace Text** — Find `_`, Replace with a space (no regex needed),
     Input: `SpeciesKey` → **Set Variable**, name it `SpacedName`.
   - **Change Case** — Capitalize Every Word, Input: `SpacedName` →
     **Set Variable**, name it `DisplayName`.
   - **Speak Text**: `For [DisplayName], Regular: [Regular] CP and Weather
     Boosted: [Boosted] CP.`

Then, in Shortcut Details (the ⓘ button), turn on **Use with Ask Siri**,
and set the phrase to something like "What's the hundo of", inserting the
step-1 text parameter into the phrase so it reads "What's the hundo of
[Text]". Siri will then fill that parameter directly from what you say
after the trigger phrase, and run the shortcut in one turn.

If your Shortcuts version doesn't offer inserting a parameter into the Siri
phrase, use two turns instead: change step 1 to an **Ask for Input** (Text)
action with prompt "Which Pokemon?" — Siri will ask, you answer, and the
rest of the shortcut runs the same.
