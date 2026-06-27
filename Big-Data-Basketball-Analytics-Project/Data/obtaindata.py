import time
import unicodedata
import pandas as pd
import numpy as np

from nba_api.stats.endpoints import (
    leaguedashplayerstats,
    leaguedashteamstats,
    drafthistory,
    leaguedashplayerbiostats,
    playerestimatedmetrics,
    teamestimatedmetrics,
    playergamelogs,
)
from nba_api.stats.static import teams as nba_teams_static

# ── Config ────────────────────────────────────────────────────────────────────
ALL_YEARS  = list(range(2024, 2027))   # SEASON_END_YEAR; e.g. 2024 = 2023-24
MIN_GP_PCT = 0.45
API_DELAY  = 1.2                        # nba_api is gentler than bref scraping

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_name(name):
    """Normalize player name to ASCII-compatible form for consistent merging."""
    if not isinstance(name, str):
        return name
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").strip()


def season_str(yr):
    """Convert season-end year to NBA API season string, e.g. 2024 → '2023-24'."""
    return f"{yr - 1}-{str(yr)[-2:]}"


def nba_api_call(endpoint_cls, retries=4, **kwargs):
    """Thin retry wrapper around any nba_api endpoint."""
    for attempt in range(retries):
        try:
            time.sleep(API_DELAY)
            result = endpoint_cls(**kwargs)
            return result.get_data_frames()[0]
        except Exception as e:
            wait = 8 * (2 ** attempt)
            print(f"    Attempt {attempt + 1} failed: {e}. Waiting {wait}s...")
            time.sleep(wait)
    return pd.DataFrame()


# ── Team abbreviation lookup (nba_api → canonical abbrev) ────────────────────

def build_team_id_to_abb():
    """Return {team_id: abbrev} using nba_api's static team list."""
    return {t["id"]: t["abbreviation"] for t in nba_teams_static.get_teams()}


TEAM_ID_TO_ABB = build_team_id_to_abb()

# Map nba_api 3-letter abbrevs to our canonical set (handles OKC=OKC, etc.)
ABB_ALIASES = {
    "NJN": "BKN", "BRK": "BKN",
    "CHO": "CHA", "CHH": "CHA",
    "NOH": "NOP", "NOK": "NOP",
    "PHO": "PHX",
    "SEA": "OKC",
    "VAN": "MEM",
    "GOS": "GSW", "GOL": "GSW",
    "SAN": "SAS", "PHL": "PHI",
    "UTH": "UTA",
    "MEM": "MEM",
    "UTA": "UTA",
}

def normalize_abb(abb):
    return ABB_ALIASES.get(abb, abb)


# ── Advanced / BPM / VORP via PlayerBioStats + GeneralStats ──────────────────
# nba_api does not expose BPM/VORP natively. We fetch:
#   - LeagueDashPlayerStats (Base)   → GP, MIN, PTS, AST, REB, STL, BLK, TOV, TS%
#   - LeagueDashPlayerBioStats       → AGE, POSITION (draft data separate)
#   - LeagueDashPlayerStats (Advanced) → PER, USG%, ORTG, DRTG (per-player on/off)
#
# BPM is not available through nba_api. We approximate it from on/off ratings:
#   BPM ≈ (PlayerORTG - TeamORTG) + (TeamDRTG - PlayerDRTG)
# Then compute VORP from the formula provided:
#   VORP = [BPM - (-2.0)] × (pct_minutes / 100) × (team_games / 82)

def get_player_stats(yr):
    """
    Fetch per-player base + advanced stats from nba_api for a given season.
    Returns the deduped per-player dataframe for that season.
    """
    season = season_str(yr)
    print(f"  Player stats (base):     {season}")

    # ── Base stats (per-game totals) ──────────────────────────────────────────
    # NOTE: LeagueDashPlayerStats returns exactly one row per player for the
    # season with no signal about team changes (no aggregate row, no
    # per-team splits). Trade detection happens separately via game logs —
    # see get_trade_splits() below.
    base = nba_api_call(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",
    )
    if base.empty:
        print(f"    WARNING: no base stats for {season}")
        return pd.DataFrame(), pd.DataFrame()

    base = base.rename(columns={
        "PLAYER_NAME": "PLAYER_NAME",
        "TEAM_ABBREVIATION": "TEAM_ABB",
        "GP": "GP",
        "MIN": "MIN_PG",
        "PTS": "PTS_PG",
        "AST": "AST_PG",
        "REB": "REB_PG",
        "STL": "STL_PG",
        "BLK": "BLK_PG",
        "TOV": "TOV_PG",
        "FGA": "FGA",
        "FTA": "FTA",
        "FGM": "FGM",
    })

    # TS% = PTS / (2 * (FGA + 0.44 * FTA))  — compute from raw counting stats
    base["TS_PCT"] = np.where(
        (base["FGA"] + 0.44 * base["FTA"]) > 0,
        base["PTS_PG"] / (2 * (base["FGA"] + 0.44 * base["FTA"])),
        np.nan,
    )

    # Total minutes for the season (needed for VORP pct_minutes)
    base["MP_TOTAL"] = base["MIN_PG"] * base["GP"]

    # ── Advanced stats (PER, USG%, on/off ORTG/DRTG for BPM approximation) ───
    print(f"  Player stats (advanced): {season}")
    adv = nba_api_call(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced",
    )

    if not adv.empty:
        adv = adv[["PLAYER_ID", "USG_PCT", "PIE"]].copy()
        # PIE (Player Impact Estimate) is nba_api's closest analog to PER.
        # We rename it PER as a practical substitute.
        adv = adv.rename(columns={"PIE": "PER"})
        adv["PER"] = pd.to_numeric(adv["PER"], errors="coerce") * 100  # PIE is 0–1; scale to ~PER range
        adv["USG_PCT"] = pd.to_numeric(adv["USG_PCT"], errors="coerce") * 100

    # ── Estimated metrics for BPM approximation ─────────────────────────────
    # PlayerEstimatedMetrics is the correct endpoint for E_OFF_RATING/E_DEF_RATING
    print(f"  Player estimated metrics:{season}")
    onoff = nba_api_call(
        playerestimatedmetrics.PlayerEstimatedMetrics,
        season=season,
        season_type="Regular Season",
    )
    if not onoff.empty:
        onoff = onoff[["PLAYER_ID", "E_OFF_RATING", "E_DEF_RATING"]].copy()
        onoff = onoff.rename(columns={
            "E_OFF_RATING": "PLAYER_ORTG",
            "E_DEF_RATING": "PLAYER_DRTG",
        })

    # ── Bio stats (age, position) ─────────────────────────────────────────────
    print(f"  Player bio stats:        {season}")
    bio = nba_api_call(
        leaguedashplayerbiostats.LeagueDashPlayerBioStats,
        season=season,
        per_mode_simple="PerGame",
    )
    if not bio.empty:
        bio = bio[["PLAYER_ID", "AGE", "PLAYER_HEIGHT", "PLAYER_WEIGHT"]].copy()

    # ── Per-36 stats ──────────────────────────────────────────────────────────
    print(f"  Player stats (per-36):   {season}")
    p36 = nba_api_call(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        per_mode_detailed="Per36",
        measure_type_detailed_defense="Base",
    )
    p36_cols = {}
    if not p36.empty:
        p36 = p36[["PLAYER_ID", "PTS", "AST", "REB", "STL", "BLK", "TOV"]].copy()
        p36 = p36.rename(columns={
            "PTS": "PTS_36", "AST": "AST_36", "REB": "REB_36",
            "STL": "STL_36", "BLK": "BLK_36", "TOV": "TOV_36",
        })

    # ── Merge everything onto base ────────────────────────────────────────────
    df = base.copy()
    for extra in [adv, onoff, bio, p36]:
        if not extra.empty and "PLAYER_ID" in extra.columns:
            df = df.merge(extra, on="PLAYER_ID", how="left")

    df["PLAYER_NAME"] = df["PLAYER_NAME"].apply(normalize_name)
    df["TEAM_ABB"]    = df["TEAM_ABB"].apply(normalize_abb)

    # ── TRADED placeholder ─────────────────────────────────────────────────────
    # This endpoint has no trade signal at all. TRADED gets overwritten in
    # main() using get_trade_splits() (real per-team game counts from game
    # logs); this is just a placeholder so the column exists here.
    df["TRADED"] = 0

    deduped = df.drop_duplicates(subset="PLAYER_NAME").copy()

    # ── BPM approximation ─────────────────────────────────────────────────────
    # For traded players the on/off ratings are already GP-weighted in the agg.
    # BPM ≈ (PlayerORTG - TeamORTG) + (TeamDRTG - PlayerDRTG)
    # We fill team ratings during the team-stats merge step in main().
    # Store raw on/off here; team deltas computed later.
    for c in ["PLAYER_ORTG", "PLAYER_DRTG"]:
        if c not in deduped.columns:
            deduped[c] = np.nan

    # OBPM/DBPM placeholders (filled after team-stats merge in main)
    deduped["OBPM"] = np.nan
    deduped["DBPM"] = np.nan
    deduped["BPM"]  = np.nan
    deduped["VORP"] = np.nan

    # ── Finalize types & season labels ───────────────────────────────────────
    for c in ["AGE", "GP", "MP_TOTAL", "PER", "TS_PCT", "USG_PCT"]:
        if c in deduped.columns:
            deduped[c] = pd.to_numeric(deduped[c], errors="coerce")

    deduped["SEASON"]          = season_str(yr)
    deduped["SEASON_END_YEAR"] = yr

    print(f"    → {len(deduped)} players loaded")

    return deduped


# ── Team stats ────────────────────────────────────────────────────────────────

def get_team_stats(yr):
    """
    Fetch team-level ORTG, DRTG, TS%, W/L from nba_api.
    Returns dict keyed by canonical team abbreviation.
    """
    season = season_str(yr)
    print(f"  Team stats:              {season}")

    base = nba_api_call(
        leaguedashteamstats.LeagueDashTeamStats,
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",
    )
    adv = nba_api_call(
        teamestimatedmetrics.TeamEstimatedMetrics,
        season=season,
        season_type="Regular Season",
    )

    if base.empty:
        print(f"    WARNING: no team base stats for {season}")
        return {}

    result = {}

    # LeagueDashTeamStats does NOT reliably return a TEAM_ABBREVIATION column
    # (it only has TEAM_ID/TEAM_NAME) — unlike the player-level endpoints.
    # Map TEAM_ID -> abbreviation via the static team list instead, falling
    # back to TEAM_ABBREVIATION only if nba_api happens to provide it.
    if "TEAM_ABBREVIATION" in base.columns:
        base["TEAM_ABB"] = base["TEAM_ABBREVIATION"].apply(normalize_abb)
    else:
        base["TEAM_ABB"] = base["TEAM_ID"].map(TEAM_ID_TO_ABB).apply(normalize_abb)
    base["TEAM_GP"]  = base["GP"]
    base["TEAM_WIN_PCT"] = base["W"] / (base["W"] + base["L"])

    # Team TS% from base counting stats
    base["TEAM_TS_PCT"] = np.where(
        (base["FGA"] + 0.44 * base["FTA"]) > 0,
        base["PTS"] / (2 * (base["FGA"] + 0.44 * base["FTA"])),
        np.nan,
    )

    team_df = base[["TEAM_ID", "TEAM_ABB", "TEAM_GP", "TEAM_WIN_PCT", "TEAM_TS_PCT"]].copy()

    # TeamEstimatedMetrics does NOT return a TEAM_ABBREVIATION column (only
    # TEAM_ID / TEAM_NAME), so we must merge it onto team_df by TEAM_ID rather
    # than trying to derive TEAM_ABB from it directly.
    if not adv.empty and "TEAM_ID" in adv.columns:
        adv = adv.rename(columns={
            "E_OFF_RATING": "TEAM_ORTG",
            "E_DEF_RATING": "TEAM_DRTG",
        })
        keep_adv = [c for c in ["TEAM_ID", "TEAM_ORTG", "TEAM_DRTG"] if c in adv.columns]
        team_df = team_df.merge(adv[keep_adv], on="TEAM_ID", how="left")
    else:
        print(f"    WARNING: TeamEstimatedMetrics missing/empty for {season}; "
              f"TEAM_ORTG/TEAM_DRTG will be NaN")
        team_df["TEAM_ORTG"] = np.nan
        team_df["TEAM_DRTG"] = np.nan

    for _, row in team_df.iterrows():
        abb = row["TEAM_ABB"]
        result[abb] = {
            "TEAM_ORTG":    row.get("TEAM_ORTG", np.nan),
            "TEAM_DRTG":    row.get("TEAM_DRTG", np.nan),
            "TEAM_TS_PCT":  row.get("TEAM_TS_PCT", np.nan),
            "TEAM_WIN_PCT": row.get("TEAM_WIN_PCT", np.nan),
            "TEAM_GP":      row.get("TEAM_GP", np.nan),
        }

    print(f"    → {len(result)} teams mapped. Keys: {sorted(result.keys())}")
    return result


# ── Draft data ────────────────────────────────────────────────────────────────

def get_draft_data():
    """
    Pull full NBA draft history from nba_api and return PLAYER_NAME,
    DRAFT_PROP (normalized pick position), UNDRAFTED flag.
    """
    print("  Draft data...")
    df = nba_api_call(drafthistory.DraftHistory)

    if df.empty:
        print("    WARNING: no draft data collected")
        return pd.DataFrame()

    df["PLAYER_NAME"] = df["PLAYER_NAME"].apply(normalize_name)
    df["_PICK_RAW"]   = pd.to_numeric(df["ROUND_PICK"], errors="coerce")
    df["_DRAFT_YR"]   = pd.to_numeric(df["SEASON"], errors="coerce")

    # Overall pick = (round - 1) * 30 + round_pick (approximation)
    df["ROUND_NUMBER"]  = pd.to_numeric(df["ROUND_NUMBER"], errors="coerce").fillna(1)
    df["_OVERALL_PICK"] = (df["ROUND_NUMBER"] - 1) * 30 + df["_PICK_RAW"].fillna(30)

    # Keep earliest/lowest pick per player
    df = df.sort_values(["PLAYER_NAME", "_OVERALL_PICK"]).drop_duplicates(
        subset="PLAYER_NAME", keep="first"
    )

    # DRAFT_PROP: normalized position within draft class (0 = 1st pick, 1 = last)
    class_size = df.groupby("_DRAFT_YR")["_OVERALL_PICK"].max().rename("_CLASS_SIZE")
    df = df.merge(class_size, on="_DRAFT_YR", how="left")
    df["DRAFT_PROP"] = (df["_OVERALL_PICK"] - 1) / df["_CLASS_SIZE"]
    df["UNDRAFTED"]  = 0

    df = df[["PLAYER_NAME", "DRAFT_PROP", "UNDRAFTED"]].copy()
    print(f"    → {len(df)} drafted players loaded")
    return df


# ── Real trade detection + per-team GP splits via game logs ───────────────────

def get_trade_splits(yr):
    """
    LeagueDashPlayerStats has no trade signal at all (one row per player,
    no aggregate row, no per-team splits). To detect trades and get real
    per-team game counts for weighting team context, we pull the full
    season's player game logs in a single call and derive both from real
    game-level team assignments.

    Returns:
      traded_players: set of normalized PLAYER_NAME values who played for
                       more than one team this season
      stint_map:       {player_name: {team_abb: games_played_with_team}}
    """
    season = season_str(yr)
    print(f"  Player game logs (trade detection): {season}")

    logs = nba_api_call(
        playergamelogs.PlayerGameLogs,
        season_nullable=season,
        season_type_nullable="Regular Season",
    )

    if logs.empty:
        print("    WARNING: no game logs collected; trade detection skipped "
              "(all players will be treated as not traded)")
        return set(), {}

    logs["PLAYER_NAME"] = logs["PLAYER_NAME"].apply(normalize_name)
    logs["TEAM_ABB"]    = logs["TEAM_ABBREVIATION"].apply(normalize_abb)

    team_counts    = logs.groupby("PLAYER_NAME")["TEAM_ABB"].nunique()
    traded_players = set(team_counts[team_counts > 1].index)

    gp_by_team = (
        logs.groupby(["PLAYER_NAME", "TEAM_ABB"])["GAME_ID"]
        .nunique()
        .reset_index(name="GP_WITH_TEAM")
    )
    stint_map = {}
    for name, grp in gp_by_team.groupby("PLAYER_NAME"):
        stint_map[name] = dict(zip(grp["TEAM_ABB"], grp["GP_WITH_TEAM"]))

    print(f"    → {len(traded_players)} players traded this season "
          f"(of {logs['PLAYER_NAME'].nunique()} total in game logs)")

    return traded_players, stint_map


def weighted_team_stats(player_name, stint_map, team_dict):
    """
    GP-weighted average of team context stats (ORTG/DRTG/TS%/WIN%) across a
    traded player's real per-team game counts, sourced from get_trade_splits.
    """
    stat_cols = ["TEAM_ORTG", "TEAM_DRTG", "TEAM_TS_PCT", "TEAM_WIN_PCT"]

    stints = stint_map.get(player_name, {})
    total_gp = sum(stints.values())
    if not stints or total_gp == 0:
        return {c: np.nan for c in stat_cols + ["TEAM_GP"]}

    result            = {c: 0.0 for c in stat_cols}
    result["TEAM_GP"] = total_gp

    for abb, gp in stints.items():
        weight = gp / total_gp
        tstats = team_dict.get(abb, {})
        for col in stat_cols:
            val = tstats.get(col, np.nan)
            if pd.notna(val):
                result[col] = result.get(col, 0.0) + val * weight

    return result



# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    adv_ded     = {}
    tdict       = {}
    trade_info  = {}

    # Pull draft data once
    print("\n=== Draft Data ===")
    draft_df = get_draft_data()

    for yr in ALL_YEARS:
        print(f"\n=== {season_str(yr)} ===")
        try:
            adv_ded[yr] = get_player_stats(yr)
        except Exception as e:
            print(f"  ERROR (player stats): {e}")

        try:
            tdict[yr] = get_team_stats(yr)
        except Exception as e:
            print(f"  ERROR (team stats): {e}")

        try:
            trade_info[yr] = get_trade_splits(yr)
        except Exception as e:
            print(f"  ERROR (trade splits): {e}")
            trade_info[yr] = (set(), {})

    # ── Merge per season ──────────────────────────────────────────────────────
    frames = []
    for yr in ALL_YEARS:
        adv = adv_ded.get(yr, pd.DataFrame())
        td  = tdict.get(yr, {})
        traded_players, stint_map = trade_info.get(yr, (set(), {}))

        if adv.empty:
            continue

        adv = adv.copy()
        adv["TRADED"] = adv["PLAYER_NAME"].isin(traded_players).astype(int)

        stat_cols = ["TEAM_ORTG", "TEAM_DRTG", "TEAM_TS_PCT", "TEAM_WIN_PCT", "TEAM_GP"]
        team_rows = []
        for _, row in adv.iterrows():
            if row["TRADED"] == 1:
                stats = weighted_team_stats(row["PLAYER_NAME"], stint_map, td)
            else:
                abb   = normalize_abb(row.get("TEAM_ABB", ""))
                stats = td.get(abb, {c: np.nan for c in stat_cols})
            team_rows.append(stats)

        team_df = pd.DataFrame(team_rows, index=adv.index)
        adv     = pd.concat([adv, team_df], axis=1)

        # ── BPM approximation (now that we have team ORTG/DRTG) ──────────────
        # BPM ≈ OBPM + DBPM
        # OBPM ≈ PlayerORTG - TeamORTG
        # DBPM ≈ TeamDRTG   - PlayerDRTG
        adv["OBPM"] = adv["PLAYER_ORTG"] - adv["TEAM_ORTG"]
        adv["DBPM"] = adv["TEAM_DRTG"]   - adv["PLAYER_DRTG"]
        adv["BPM"]  = adv["OBPM"] + adv["DBPM"]

        # ── VORP approximation ───────────────────────────────────────────────
        # VORP = [BPM - (-2.0)] × (pct_minutes / 100) × (team_games / 82)
        # pct_minutes = MP_TOTAL / (TEAM_GP * 240)  [240 min/game for 5 players]
        adv["_PCT_MIN"] = adv["MP_TOTAL"] / (adv["TEAM_GP"] * 240) * 100
        adv["VORP"] = (adv["BPM"] - (-2.0)) * (adv["_PCT_MIN"] / 100) * (adv["TEAM_GP"] / 82)
        adv.drop(columns=["_PCT_MIN"], inplace=True)

        # GP eligibility
        gp_num         = pd.to_numeric(adv.get("GP", pd.Series(dtype=float)), errors="coerce")
        adv["GP_PCT"]  = gp_num / adv["TEAM_GP"]
        adv["SEASON_END_YEAR"] = yr

        frames.append(adv)

    if not frames:
        print("ERROR: no data collected")
        return

    full = pd.concat(frames, ignore_index=True)
    full = full.sort_values(["PLAYER_NAME", "SEASON_END_YEAR"]).reset_index(drop=True)

    # ── Merge draft data ──────────────────────────────────────────────────────
    if not draft_df.empty:
        full = full.merge(draft_df, on="PLAYER_NAME", how="left")
        full["UNDRAFTED"]  = full["UNDRAFTED"].fillna(1).astype(int)
        full["DRAFT_PROP"] = full["DRAFT_PROP"].fillna(1.0)
    else:
        full["UNDRAFTED"]  = 0
        full["DRAFT_PROP"] = np.nan

    # ── GP eligibility ────────────────────────────────────────────────────────
    full["GP_ELIGIBLE"] = (full["GP_PCT"] >= MIN_GP_PCT).astype(int)

    # ── Season number ─────────────────────────────────────────────────────────
    full["SEASON_NUM"] = full.groupby("PLAYER_NAME").cumcount() + 1

    # ── Keep only players with >= 3 seasons in the window ────────────────────
    players_with_3 = (
        full.groupby("PLAYER_NAME")["SEASON_END_YEAR"]
        .count()[lambda s: s >= 3]
        .index
    )
    full = full[full["PLAYER_NAME"].isin(players_with_3)].copy()

    # ── Lags and differentials ────────────────────────────────────────────────
    grp = full.groupby("PLAYER_NAME")

    full["LAST_TRADED"] = grp["TRADED"].shift(1)

    lag_cols = ["PTS_36", "AST_36", "REB_36", "STL_36", "BLK_36", "TOV_36",
                "USG_PCT", "TS_PCT", "PER", "BPM", "VORP", "GP_PCT"]

    for col in lag_cols:
        if col in full.columns:
            full[f"LAST_{col}"]      = grp[col].shift(1)
            full[f"LAST_{col}_DIFF"] = grp[col].shift(1) - grp[col].shift(2)

    team_pred_cols = ["TEAM_ORTG", "TEAM_DRTG", "TEAM_WIN_PCT", "TEAM_TS_PCT"]
    for col in team_pred_cols:
        if col in full.columns:
            full[f"LAST_{col}"]      = grp[col].shift(1)
            full[f"LAST_{col}_DIFF"] = grp[col].shift(1) - grp[col].shift(2)

    for col in ["PER", "BPM", "VORP"]:
        if col in full.columns:
            full[f"{col}_DIFF"] = full[col] - grp[col].shift(1)

    # ── Position dummies ──────────────────────────────────────────────────────
    pos_map = {
        "PG": "Guard",   "SG": "Guard",   "G": "Guard",
        "SF": "Forward", "PF": "Forward", "F": "Forward",
        "C":  "Center",
        "G-F": "Guard-Forward", "F-G": "Guard-Forward",
        "F-C": "Forward-Center", "C-F": "Forward-Center",
    }
    if "POSITION" in full.columns:
        full["POSITION_CLEAN"] = full["POSITION"].map(pos_map).fillna("Forward")
        pos_dummies = pd.get_dummies(full["POSITION_CLEAN"], prefix="POS", drop_first=True)
        full = pd.concat([full, pos_dummies], axis=1)

    # ── Keep only rows where SEASON_NUM >= 3 ─────────────────────────────────
    out_df = full[full["SEASON_NUM"] >= 3].copy()

    # ── Drop rows with missing team context ───────────────────────────────────
    team_required         = ["LAST_TEAM_ORTG_DIFF", "LAST_TEAM_DRTG_DIFF"]
    team_required_present = [c for c in team_required if c in out_df.columns]
    if team_required_present:
        before  = len(out_df)
        out_df  = out_df.dropna(subset=team_required_present).copy()
        dropped = before - len(out_df)
        if dropped > 0:
            print(f"  Dropped {dropped} rows with missing LAST_TEAM_ORTG/DRTG_DIFF")

    # ── Keep only rows that pass the games-played eligibility test ───────────
    before_gp = len(out_df)
    out_df = out_df[out_df["GP_ELIGIBLE"] == 1].copy()
    dropped_gp = before_gp - len(out_df)
    if dropped_gp > 0:
        print(f"  Dropped {dropped_gp} rows failing GP_ELIGIBLE "
              f"(GP_PCT < {MIN_GP_PCT})")

    # ── Select output columns ─────────────────────────────────────────────────
    personal    = ["PLAYER_NAME", "SEASON", "SEASON_NUM", "AGE", "LAST_TRADED",
                   "DRAFT_PROP", "UNDRAFTED", "GP_PCT", "GP_ELIGIBLE"]
    pos_cols    = [c for c in out_df.columns if c.startswith("POS_")]
    player_last = [f"LAST_{c}" for c in
                   ["PTS_36", "AST_36", "REB_36", "STL_36", "BLK_36", "TOV_36",
                    "USG_PCT", "TS_PCT"] if f"LAST_{c}" in out_df.columns]
    player_mom  = [f"LAST_{c}_DIFF" for c in
                   ["PTS_36", "AST_36", "REB_36", "STL_36", "BLK_36", "TOV_36",
                    "USG_PCT", "TS_PCT"] if f"LAST_{c}_DIFF" in out_df.columns]
    team_last   = [f"LAST_{c}" for c in team_pred_cols if f"LAST_{c}" in out_df.columns]
    team_mom    = [f"LAST_{c}_DIFF" for c in team_pred_cols if f"LAST_{c}_DIFF" in out_df.columns]
    adv_pred    = (
        [f"LAST_{v}"      for v in ["PER", "BPM", "VORP"] if f"LAST_{v}"      in out_df.columns] +
        [f"LAST_{v}_DIFF" for v in ["PER", "BPM", "VORP"] if f"LAST_{v}_DIFF" in out_df.columns]
    )
    dep_vars    = [f"{v}_DIFF" for v in ["PER", "BPM", "VORP"] if f"{v}_DIFF" in out_df.columns]

    final_cols = (personal + pos_cols + player_last + player_mom +
                  team_last + team_mom + adv_pred + dep_vars)
    final_cols = [c for c in final_cols if c in out_df.columns]
    out = out_df[final_cols].copy()

    # ── Export ────────────────────────────────────────────────────────────────
    out.to_csv("nba_oos.csv", index=False)
    print(f"\n✓ Saved nba_oos.csv")
    print(f"  Seasons:        {sorted(out['SEASON'].unique())}")
    print(f"  Players:        {out['PLAYER_NAME'].nunique()}")
    print(f"  Rows (total):   {len(out)}  [all GP_ELIGIBLE==1, GP_PCT >= {MIN_GP_PCT}]")
    print(f"  Traded last season: {int(out['LAST_TRADED'].sum())}")
    if "UNDRAFTED" in out.columns:
        print(f"  Undrafted players:  {int(out['UNDRAFTED'].sum())} rows")
    if "DRAFT_PROP" in out.columns:
        print(f"  Draft prop coverage:{out['DRAFT_PROP'].notna().mean() * 100:.1f}%")
    print(f"\nTeam stat coverage (% non-null):")
    for col in ["LAST_TEAM_ORTG_DIFF", "LAST_TEAM_DRTG_DIFF",
                "LAST_TEAM_TS_PCT_DIFF"]:
        if col in out.columns:
            print(f"  {col}: {out[col].notna().mean() * 100:.1f}%")


if __name__ == "__main__":
    main()
