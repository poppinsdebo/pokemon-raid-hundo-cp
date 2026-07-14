"""
Generates data/hundo_cp.json: for every Pokemon species/form, the CP of a
100% IV (15/15/15) catch at raid catch levels (20 normal, 25 weather-boosted).

Source of truth: PokeMiners' mirror of Niantic's GAME_MASTER file, which
also contains the CP multiplier (CPM) table used in the CP formula.
"""
import json
import math
import re
import urllib.request
from datetime import datetime, timezone

GAME_MASTER_URL = "https://raw.githubusercontent.com/PokeMiners/game_masters/master/latest/latest.json"
RAID_CATCH_LEVELS = {"level20": 20, "level25": 25}
OUTPUT_PATH = "data/hundo_cp.json"

# Regional-form suffixes that people commonly say as a leading adjective
# ("Alolan Raichu") rather than trailing ("Raichu Alola"). Maps the
# GAME_MASTER suffix to the spoken adjective.
REGIONAL_ADJECTIVES = {
    "ALOLA": "ALOLAN",
    "GALARIAN": "GALARIAN",
    "HISUIAN": "HISUIAN",
    "PALDEA": "PALDEAN",
}

# Extra spoken phrases for names Siri dictation tends to mangle (punctuation,
# split compound words, "Jr."/"Z" read as separate words, etc.).
SPECIAL_ALIASES = {
    "HO_OH": ["ho oh", "hooh"],
    "MIME_JR": ["mime jr", "mime junior"],
    "MR_MIME": ["mr mime", "mister mime"],
    "MR_MIME_GALARIAN": ["galarian mr mime", "galarian mister mime"],
    "MR_RIME": ["mr rime", "mister rime"],
    "JANGMO_O": ["jangmo o", "jangmoo"],
    "HAKAMO_O": ["hakamo o", "hakamoo"],
    "KOMMO_O": ["kommo o", "kommoo"],
    "PORYGON_Z": ["porygon z"],
    "TYPE_NULL": ["type null"],
    "NIDORAN_FEMALE": ["nidoran female"],
    "NIDORAN_MALE": ["nidoran male"],
    "FARFETCHD": ["farfetchd", "farfetch d"],
    "FARFETCHD_GALARIAN": ["galarian farfetchd", "galarian farfetch d"],
    "SIRFETCHD": ["sirfetchd", "sirfetch d"],
}


def normalize(text):
    """Lowercase, alphanumeric-only, no spaces — matches how the Shortcut
    normalizes whatever Siri transcribes."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def build_aliases(key):
    """All spoken-phrase keys (already normalize()d) that should resolve to
    this pokemon_out key."""
    parts = key.split("_")
    aliases = {normalize(" ".join(parts))}

    if len(parts) >= 2:
        suffix = parts[-1]
        species_parts = parts[:-1]
        if suffix in REGIONAL_ADJECTIVES:
            adjective = REGIONAL_ADJECTIVES[suffix]
            aliases.add(normalize(adjective + " " + " ".join(species_parts)))
            aliases.add(normalize(suffix + " " + " ".join(species_parts)))

    for phrase in SPECIAL_ALIASES.get(key, []):
        aliases.add(normalize(phrase))

    return aliases


def fetch_game_master():
    with urllib.request.urlopen(GAME_MASTER_URL, timeout=60) as resp:
        return json.load(resp)


def extract_cp_multipliers(game_master):
    for entry in game_master:
        if entry.get("templateId") == "PLAYER_LEVEL_SETTINGS":
            cpm_list = entry["data"]["playerLevel"]["cpMultiplier"]
            # cpm_list[0] is level 1
            return {level: cpm_list[level - 1] for level in range(1, len(cpm_list) + 1)}
    raise RuntimeError("PLAYER_LEVEL_SETTINGS not found in game master")


def extract_species_forms(game_master):
    """Returns {pokemonId: {formSuffix: {"attack":.., "defense":.., "stamina":..}}}
    formSuffix is "" for the base/normal form."""
    species = {}
    for entry in game_master:
        settings = entry.get("data", {}).get("pokemonSettings")
        if not settings or "stats" not in settings:
            continue
        pokemon_id = settings["pokemonId"]
        stats = settings["stats"]
        base_stats = {
            "attack": stats["baseAttack"],
            "defense": stats["baseDefense"],
            "stamina": stats["baseStamina"],
        }
        form = settings.get("form", pokemon_id)
        suffix = ""
        if form != pokemon_id and form != f"{pokemon_id}_NORMAL":
            suffix = form[len(pokemon_id) + 1:] if form.startswith(pokemon_id) else form
        species.setdefault(pokemon_id, {})[suffix] = base_stats
    return species


def pick_canonical_forms(forms_by_suffix):
    """Collapses cosmetic costumes (identical stats to the base form) and
    keeps only the base form plus real alternate forms (Alolan, Mega, etc.),
    which have different base stats."""
    base_stats = forms_by_suffix.get("") or next(iter(forms_by_suffix.values()))
    result = {"": base_stats}
    for suffix, stats in forms_by_suffix.items():
        if suffix and stats != base_stats:
            result[suffix] = stats
    return result


def calc_cp(attack, defense, stamina, iv, cpm):
    a, d, s = attack + iv, defense + iv, stamina + iv
    cp = math.floor((a * math.sqrt(d) * math.sqrt(s) * cpm ** 2) / 10)
    return max(cp, 10)


def build_dataset(game_master):
    cpm = extract_cp_multipliers(game_master)
    species_forms = extract_species_forms(game_master)

    pokemon_out = {}
    for pokemon_id, forms_by_suffix in species_forms.items():
        for suffix, stats in pick_canonical_forms(forms_by_suffix).items():
            key = pokemon_id if not suffix else f"{pokemon_id}_{suffix}"
            cp_by_level = {
                label: calc_cp(stats["attack"], stats["defense"], stats["stamina"], 15, cpm[level])
                for label, level in RAID_CATCH_LEVELS.items()
            }
            pokemon_out[key] = {
                "base_stats": stats,
                "hundo_cp": cp_by_level,
            }

    lookup = {}
    for key in pokemon_out:
        for alias in build_aliases(key):
            lookup[alias] = key

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": GAME_MASTER_URL,
        "iv": {"attack": 15, "defense": 15, "stamina": 15},
        "catch_levels": RAID_CATCH_LEVELS,
        "pokemon": dict(sorted(pokemon_out.items())),
        "lookup": dict(sorted(lookup.items())),
    }


def main():
    game_master = fetch_game_master()
    dataset = build_dataset(game_master)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(dataset['pokemon'])} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
