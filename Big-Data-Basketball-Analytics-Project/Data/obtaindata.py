import time, re, requests, unicodedata
import pandas as pd
import numpy as np
from io import StringIO

def normalize_name(name):
"""
    Normalize player name to ASCII-compatible form for consistent merging.
    Converts accented characters to their base form:
"""
    if not isinstance(name, str):
        return name
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").strip()

ALL_YEARS  = list(range(2024, 2027))  # start 2008 for lag history; 2008=2007-08 includes Seattle
MIN_GP_PCT = 0.45
API_DELAY  = 4.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MULTI_TEAM_SENTINELS = {"TOT", "2TM", "3TM", "4TM", "5TM"}

TEAM_ABB = {
    "ATL","BOS","BKN","NJN","CHA","CHH","CHO","CHI","CLE","DAL",
    "DEN","DET","GSW","HOU","IND","LAC","LAL","MEM","MIA","MIL",
    "MIN","NOP","NOH","NOK","NYK","OKC","ORL","PHI","PHX","POR",
    "SAC","SAS","TOR","UTA","WAS","SEA","VAN",
}
#normalize player row abbreviation for each team
ABB_ALIASES = {
    "NJN": "BKN",  "BRK": "BKN",
    "CHO": "CHA",  "CHH": "CHA",
    "NOH": "NOP",  "NOK": "NOP",
    "PHO": "PHX",
    "SEA": "OKC",
    "VAN": "MEM",
    "GOS": "GSW",  "GOL": "GSW",
    "SAN": "SAS",  "PHL": "PHI",
    "UTH": "UTA",  "MEM": "MEM",
}

def normalize_abb(abb):
    """Resolve abbreviation aliases to canonical form."""
    return ABB_ALIASES.get(abb, abb)

def bref_season_str(yr):
    return f"{yr-1}-{str(yr)[-2:]}"

def fetch_html(url, retries=4):
    for attempt in range(retries):
        try:
            time.sleep(API_DELAY if attempt == 0 else 0)
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 404: return None
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait); continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            wait = 8 * (2 ** attempt)
            print(f"    Attempt {attempt+1} failed: {e}. Waiting {wait}s...")
            time.sleep(wait)
    return None

def parse_table(html, table_id):
    if not html: return pd.DataFrame()
    clean = html.replace("<!--","").replace("-->","")
    try:
        dfs = pd.read_html(StringIO(clean), attrs={"id": table_id})
        return dfs[0] if dfs else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def norm_cols(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            " ".join(str(c).strip() for c in col
                     if str(c).strip() not in ("nan","")).strip()
            for col in df.columns
        ]
    def clean(c):
        c = str(c).strip()
        c = re.sub(r"^(Unnamed:[\s]*[\d]+_level_[\d]+[\s]*)+", "", c).strip()
        return c
    df.columns = [clean(c) for c in df.columns]
    return df

def drop_junk_rows(df, name_col):
    df = df[df[name_col].notna()].copy()
    df = df[~df[name_col].isin([
        name_col, "Player", "Team", "Tm", "Rk",
        "League Average", "Lg Avg", "Average", "", "Team Totals"
    ])].copy()
    df = df[~df[name_col].str.match(r"^\d+$", na=False)].copy()
    df[name_col] = df[name_col].str.replace("*","",regex=False).str.strip()
    return df

def find_col(df, candidates):
    for c in candidates:
        if c in df.columns: return c
    return None

#Advanced Stats
def get_advanced(yr):
    print(f"  Advanced:  {bref_season_str(yr)}")
    html = fetch_html(
        f"https://www.basketball-reference.com/leagues/NBA_{yr}_advanced.html"
    )
    df = parse_table(html, "advanced")
    if df.empty: return pd.DataFrame(), pd.DataFrame()

    df = norm_cols(df)
    nc = find_col(df, ["Player","player","PLAYER"])
    if not nc:
        print(f"    WARNING: no Player col. Cols: {df.columns.tolist()[:8]}")
        return pd.DataFrame(), pd.DataFrame()
    if nc != "Player": df = df.rename(columns={nc: "Player"})

    tc = find_col(df, ["Tm","Team","team","tm"])
    if tc and tc != "Tm": df = df.rename(columns={tc: "Tm"})
    if "Tm" not in df.columns: df["Tm"] = "UNK"

    df = df[df["Player"].notna()].copy()
    df = df[~df["Player"].isin(["Player",""])].copy()
    df = df[~df["Player"].str.match(r"^\d+$", na=False)].copy()
    df["Player"] = df["Player"].str.replace("*","",regex=False).str.strip()
    df["Player"] = df["Player"].apply(normalize_name)

    #Trade detection
    real_rows  = df[~df["Tm"].isin(MULTI_TEAM_SENTINELS)]
    team_count = real_rows.groupby("Player")["Tm"].nunique()
    traded_set = set(team_count[team_count > 1].index)
    df["TRADED"] = df["Player"].isin(traded_set).astype(int)
    raw_df = df.copy()

    def keep_row(grp):
        if grp["TRADED"].iloc[0] == 1:
            for sentinel in ["TOT","2TM","3TM","4TM","5TM"]:
                s = grp[grp["Tm"] == sentinel]
                if not s.empty: return s.iloc[[0]]
            return grp.iloc[[0]]
        else:
            non_sent = grp[~grp["Tm"].isin(MULTI_TEAM_SENTINELS)]
            return non_sent.iloc[[0]] if not non_sent.empty else grp.iloc[[0]]

    deduped = pd.concat(
        [keep_row(grp) for _, grp in df.groupby("Player", sort=False)],
        ignore_index=True
    )

    col_map = {
        "Player":"PLAYER_NAME","Age":"AGE","Tm":"TEAM_ABB",
        "Pos":"POSITION","G":"GP","MP":"MP_TOTAL",
        "PER":"PER","TS%":"TS_PCT","USG%":"USG_PCT",
        "BPM":"BPM","OBPM":"OBPM","DBPM":"DBPM","VORP":"VORP",
        "TRADED":"TRADED",
    }
    deduped = deduped.rename(columns={k:v for k,v in col_map.items() if k in deduped.columns})
    if "PLAYER_NAME" in deduped.columns:
        deduped["PLAYER_NAME"] = deduped["PLAYER_NAME"].apply(normalize_name)
    for c in ["AGE","GP","MP_TOTAL","PER","TS_PCT","USG_PCT","BPM","VORP"]:
        if c in deduped.columns:
            deduped[c] = pd.to_numeric(deduped[c], errors="coerce")

    deduped["SEASON"]          = bref_season_str(yr)
    deduped["SEASON_END_YEAR"] = yr
    return deduped, raw_df

#Per-36 basic stats
def get_per36(yr):
    print(f"  Per-36:    {bref_season_str(yr)}")
    urls = [
        f"https://www.basketball-reference.com/leagues/NBA_{yr}_per_36_minutes.html",
        f"https://www.basketball-reference.com/leagues/NBA_{yr}_per_minute.html",
    ]
    tids = ["per_minute_stats","per_36_stats","per_minute","stats"]
    df = pd.DataFrame()
    for url in urls:
        html = fetch_html(url)
        if not html: continue
        for tid in tids:
            df = parse_table(html, tid)
            if not df.empty: break
        if not df.empty: break

    if df.empty:
        print(f"    WARNING: no per-36 for {yr}")
        return pd.DataFrame()

    df = norm_cols(df)
    nc = find_col(df, ["Player","player"])
    if not nc: return pd.DataFrame()
    if nc != "Player": df = df.rename(columns={nc: "Player"})

    tc = find_col(df, ["Tm","Team"])
    if tc and tc != "Tm": df = df.rename(columns={tc: "Tm"})
    if "Tm" not in df.columns: df["Tm"] = "UNK"

    df = df[df["Player"].notna() & ~df["Player"].isin(["Player",""])].copy()
    df = df[~df["Player"].str.match(r"^\d+$", na=False)].copy()
    df["Player"] = df["Player"].str.replace("*","",regex=False).str.strip()
    df["Player"] = df["Player"].apply(normalize_name)

    real_rows  = df[~df["Tm"].isin(MULTI_TEAM_SENTINELS)]
    traded_set = set(
        real_rows.groupby("Player")["Tm"].nunique()[lambda s: s > 1].index
    )
    def keep_row_p36(grp):
        player_name = grp["Player"].iloc[0]
        if player_name in traded_set:
            for s in ["TOT","2TM","3TM"]:
                sub = grp[grp["Tm"] == s]
                if not sub.empty: return sub.iloc[[0]]
        non_sent = grp[~grp["Tm"].isin(MULTI_TEAM_SENTINELS)]
        return non_sent.iloc[[0]] if not non_sent.empty else grp.iloc[[0]]

    df = pd.concat(
        [keep_row_p36(grp) for _, grp in df.groupby("Player", sort=False)],
        ignore_index=True
    )

    col_map = {
        "Player":"PLAYER_NAME",
        "PTS":"PTS_36","AST":"AST_36","TRB":"REB_36",
        "STL":"STL_36","BLK":"BLK_36","TOV":"TOV_36",
    }
    df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})
    if "PLAYER_NAME" in df.columns:
        df["PLAYER_NAME"] = df["PLAYER_NAME"].apply(normalize_name)
    keep = ["PLAYER_NAME"] + [v for v in col_map.values() if v != "PLAYER_NAME" and v in df.columns]
    df   = df[keep].copy()
    for c in keep[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["SEASON_END_YEAR"] = yr
    return df

#Team stats
def get_team_stats(yr):
    print(f"  Team stats:{bref_season_str(yr)}")

    if yr >= 2016:
        url_tids = [
            (f"https://www.basketball-reference.com/leagues/NBA_{yr}_ratings.html", "ratings"),
            (f"https://www.basketball-reference.com/leagues/NBA_{yr}.html",          "advanced-team"),
        ]
    else:
        url_tids = [
            (f"https://www.basketball-reference.com/leagues/NBA_{yr}.html", "advanced-team"),
        ]

    df = pd.DataFrame()
    for url, tid in url_tids:
        html = fetch_html(url)
        if not html: continue
        df = parse_table(html, tid)
        if not df.empty: break

    if df.empty:
        print(f"    WARNING: no team stats for {yr}")
        return {}

    df = norm_cols(df)
    tm_col   = find_col(df, ["Tm","tm"])
    name_col = find_col(df, ["Team","team"])

    if not tm_col and not name_col:
        print(f"    WARNING: no team col. Cols: {df.columns.tolist()}")
        return {}

    id_col = tm_col if tm_col else name_col
    df = df[df[id_col].notna()].copy()
    df = df[~df[id_col].isin([
        id_col,"Tm","Team","League Average","Lg Avg","Average","","Totals"
    ])].copy()
    df[id_col] = df[id_col].str.replace("*","",regex=False).str.strip()

    rename_map = {}
    assigned   = set()
    for col in df.columns:
        cl = col.lower().replace(" ","").replace("/","").replace("-","").replace("_","")
        if col == id_col: pass
        elif "pace" in cl and "TEAM_PACE"    not in assigned: rename_map[col]="TEAM_PACE";    assigned.add("TEAM_PACE")
        elif "ortg" in cl and "TEAM_ORTG"    not in assigned: rename_map[col]="TEAM_ORTG";    assigned.add("TEAM_ORTG")
        elif "drtg" in cl and "TEAM_DRTG"    not in assigned: rename_map[col]="TEAM_DRTG";    assigned.add("TEAM_DRTG")
        elif "ts"   in cl and "%" in col and "TEAM_TS_PCT" not in assigned: rename_map[col]="TEAM_TS_PCT"; assigned.add("TEAM_TS_PCT")
        elif cl=="sos"   and "TEAM_SOS"      not in assigned: rename_map[col]="TEAM_SOS";     assigned.add("TEAM_SOS")
        elif cl=="w"     and "TEAM_W"        not in assigned: rename_map[col]="TEAM_W";       assigned.add("TEAM_W")
        elif cl=="l"     and "TEAM_L"        not in assigned: rename_map[col]="TEAM_L";       assigned.add("TEAM_L")

    df = df.rename(columns=rename_map)
    for col in ["TEAM_PACE","TEAM_ORTG","TEAM_DRTG","TEAM_TS_PCT","TEAM_SOS","TEAM_W","TEAM_L"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "TEAM_W" in df.columns and "TEAM_L" in df.columns:
        df["TEAM_WIN_PCT"] = df["TEAM_W"] / (df["TEAM_W"] + df["TEAM_L"])
        df["TEAM_GP"]      = df["TEAM_W"] + df["TEAM_L"]

    stat_cols = [c for c in ["TEAM_PACE","TEAM_ORTG","TEAM_DRTG","TEAM_TS_PCT",
                               "TEAM_SOS","TEAM_WIN_PCT","TEAM_GP"] if c in df.columns]
    result = {}
    for _, row in df.iterrows():
        key = row[id_col]
        if tm_col:
            abb = key
        else:
            abb = None
            key_lower = key.lower()
            abb_to_name = {
                "ATL":"atlanta hawks","BOS":"boston celtics","BKN":"brooklyn nets",
                "CHA":"charlotte hornets","CHI":"chicago bulls","CLE":"cleveland cavaliers",
                "DAL":"dallas mavericks","DEN":"denver nuggets","DET":"detroit pistons",
                "GSW":"golden state warriors","HOU":"houston rockets","IND":"indiana pacers",
                "LAC":"los angeles clippers","LAL":"los angeles lakers","MEM":"memphis grizzlies",
                "MIA":"miami heat","MIL":"milwaukee bucks","MIN":"minnesota timberwolves",
                "NOP":"new orleans pelicans","NYK":"new york knicks","OKC":"oklahoma city thunder",
                "ORL":"orlando magic","PHI":"philadelphia 76ers","PHX":"phoenix suns",
                "POR":"portland trail blazers","SAC":"sacramento kings","SAS":"san antonio spurs",
                "TOR":"toronto raptors","UTA":"utah jazz","WAS":"washington wizards",
            }
            for a, name in abb_to_name.items():
                if name in key_lower or key_lower in name:
                    abb = a; break
        if not abb: continue
        result[abb] = {col: row.get(col, np.nan) for col in stat_cols}

    print(f"    → {len(result)} teams mapped. Keys: {sorted(result.keys())}")
    return result

#Draft position data
def get_draft_data():

    print("  Draft data...")
    # bball-ref draft index — covers all years
    url  = "https://www.basketball-reference.com/draft/"
    # Each year's draft is on a separate page; we'll pull each draft class
    # for the years relevant to our dataset (players drafted ~1990-2025)
    # and concatenate them.
    all_picks = []

    for draft_yr in range(1985, 2026):
        html = fetch_html(
            f"https://www.basketball-reference.com/draft/NBA_{draft_yr}.html"
        )
        #bball-ref draft pages use table id "stats"
        df = parse_table(html, "stats")
        if df.empty:
            continue

        df = norm_cols(df)

        #Diagnostic on first year to confirm columns
        if draft_yr == 2020:
            print(f"    [DIAG] Draft table cols: {df.columns.tolist()[:12]}")
            print(f"    [DIAG] First data row: {df.iloc[1].tolist()[:8]}")

        #bball-ref draft table flattens MultiIndex to "Round 1 Player",
        #"Round 2 Player" etc. Find whichever column contains "Player".
        nc = next((c for c in df.columns if "player" in c.lower()), None)
        if not nc:
            continue
        if nc != "Player":
            df = df.rename(columns={nc: "Player"})

        #Drop header/junk rows
        df = df[df["Player"].notna()].copy()
        df = df[~df["Player"].isin(["Player",""])].copy()
        df = df[~df["Player"].str.match(r"^\d+$", na=False)].copy()
        df["Player"] = df["Player"].str.replace("*","",regex=False).str.strip()
        df["Player"] = df["Player"].apply(normalize_name)

        # bball-ref draft table uses "Pk" for overall pick number.
        # After MultiIndex flattening it stays as "Pk" (it's in the unnamed
        # top-level group so norm_cols strips the prefix leaving just "Pk").
        # Also search for any column containing "pk" as fallback.
        pk_col = find_col(df, ["Pk","pk","Pick","pick","Overall","overall"])
        if not pk_col:
            pk_col = next((c for c in df.columns if c.lower() == "pk"), None)
        if not pk_col:
            if draft_yr == 2020:
                print(f"    [DIAG] No pick col found. Cols: {df.columns.tolist()}")
            continue

        df["_PICK_RAW"] = pd.to_numeric(df[pk_col], errors="coerce")
        df["_DRAFT_YR"] = draft_yr

        all_picks.append(df[["Player","_PICK_RAW","_DRAFT_YR"]].copy())

    if not all_picks:
        print("    WARNING: no draft data collected")
        return pd.DataFrame()

    picks = pd.concat(all_picks, ignore_index=True)

    #Keep only the earliest draft year where player was actually picked
    picks = picks.sort_values(["Player","_PICK_RAW"]).drop_duplicates(
        subset="Player", keep="first"
    )

    #Compute DRAFT_PROP per draft class
    class_size = picks.groupby("_DRAFT_YR")["_PICK_RAW"].max().rename("_CLASS_SIZE")
    picks = picks.merge(class_size, on="_DRAFT_YR", how="left")

    picks["DRAFT_PROP"] = (picks["_PICK_RAW"] - 1) / picks["_CLASS_SIZE"]
    picks["UNDRAFTED"]  = 0  # everyone in this table was drafted

    picks = picks.rename(columns={"Player": "PLAYER_NAME"})
    picks = picks[["PLAYER_NAME","DRAFT_PROP","UNDRAFTED"]].copy()

    print(f"    → {len(picks)} drafted players loaded")
    return picks


#Weighted team stats for traded players
def weighted_team_stats(player_name, raw_df, team_dict):
    stat_cols = ["TEAM_PACE","TEAM_ORTG","TEAM_DRTG","TEAM_TS_PCT",
                 "TEAM_SOS","TEAM_WIN_PCT"]

    player_rows = raw_df[
        (raw_df["Player"].apply(normalize_name) == normalize_name(player_name)) &
        (~raw_df["Tm"].isin(MULTI_TEAM_SENTINELS))
    ].copy()

    if player_rows.empty:
        return {c: np.nan for c in stat_cols + ["TEAM_GP"]}

    gp_col = find_col(player_rows, ["G","GP","g"])
    if gp_col:
        player_rows["_GP"] = pd.to_numeric(player_rows[gp_col], errors="coerce").fillna(0)
    else:
        player_rows["_GP"] = 1.0

    total_gp = player_rows["_GP"].sum()
    if total_gp == 0:
        return {c: np.nan for c in stat_cols + ["TEAM_GP"]}

    result = {c: 0.0 for c in stat_cols}
    result["TEAM_GP"] = total_gp

    for _, r in player_rows.iterrows():
        abb    = normalize_abb(r["Tm"])
        weight = r["_GP"] / total_gp
        tstats = team_dict.get(abb, {})
        for col in stat_cols:
            val = tstats.get(col, np.nan)
            if pd.notna(val):
                result[col] = result.get(col, 0.0) + val * weight

    return result

#Main 
def main():
    adv_ded = {}
    adv_raw = {}
    per36   = {}
    tdict   = {}

    #Pull draft data
    print("\n=== Draft Data ===")
    draft_df = get_draft_data()

    for yr in ALL_YEARS:
        print(f"\n=== {bref_season_str(yr)} ===")
        try:
            d, r        = get_advanced(yr)
            adv_ded[yr] = d
            adv_raw[yr] = r
            per36[yr]   = get_per36(yr)
            tdict[yr]   = get_team_stats(yr)
        except Exception as e:
            print(f"  ERROR: {e}")

    #Merge per season
    frames = []
    for yr in ALL_YEARS:
        adv = adv_ded.get(yr, pd.DataFrame())
        p36 = per36.get(yr, pd.DataFrame())
        td  = tdict.get(yr, {})
        raw = adv_raw.get(yr, pd.DataFrame())

        if adv.empty: continue

        if not p36.empty:
            adv = adv.merge(p36, on=["PLAYER_NAME","SEASON_END_YEAR"], how="left")

        stat_cols = ["TEAM_PACE","TEAM_ORTG","TEAM_DRTG","TEAM_TS_PCT",
                     "TEAM_SOS","TEAM_WIN_PCT","TEAM_GP"]
        team_rows = []
        for _, row in adv.iterrows():
            if row.get("TRADED", 0) == 1:
                stats = weighted_team_stats(row["PLAYER_NAME"], raw, td)
            else:
                abb   = normalize_abb(row.get("TEAM_ABB",""))
                stats = td.get(abb, {c: np.nan for c in stat_cols})
            team_rows.append(stats)

        team_df      = pd.DataFrame(team_rows, index=adv.index)
        adv          = pd.concat([adv, team_df], axis=1)
        gp_num       = pd.to_numeric(adv.get("GP", pd.Series(dtype=float)), errors="coerce")
        adv["GP_PCT"]          = gp_num / adv["TEAM_GP"]
        adv["SEASON_END_YEAR"] = yr

        #Diagnostic: report which players are missing ORTG this season
        missing_ortg = adv[adv["TEAM_ORTG"].isna()][["PLAYER_NAME","TEAM_ABB","TRADED"]].copy()
        if not missing_ortg.empty:
            print(f"    [DIAG {yr}] {len(missing_ortg)} players missing TEAM_ORTG:")
            print(missing_ortg.to_string(index=False))

        frames.append(adv)

    if not frames:
        print("ERROR: no data collected"); return

    full = pd.concat(frames, ignore_index=True)
    full = full.sort_values(["PLAYER_NAME","SEASON_END_YEAR"]).reset_index(drop=True)

    #Merge draft data
    if not draft_df.empty:
        full = full.merge(draft_df, on="PLAYER_NAME", how="left")
        # Fill undrafted players
        full["UNDRAFTED"]  = full["UNDRAFTED"].fillna(1).astype(int)
        full["DRAFT_PROP"] = full["DRAFT_PROP"].fillna(1.0)
    else:
        full["UNDRAFTED"]  = 0
        full["DRAFT_PROP"] = np.nan

    #Checks if eligible proportion of games played is satisfied
    full["GP_ELIGIBLE"] = (full["GP_PCT"] >= MIN_GP_PCT).astype(int)

    #Season number (all seasons count, regardless of GP%)
    full["SEASON_NUM"] = full.groupby("PLAYER_NAME").cumcount() + 1

    #Keep only players with >= 3 seasons in the window
    full.groupby("PLAYER_NAME")["SEASON_END_YEAR"].count()[lambda s: s >= 3].index)
    full = full[full["PLAYER_NAME"].isin(players_with_3)].copy()

    #Lags and differentials
    grp = full.groupby("PLAYER_NAME")

    # Lag TRADED binary
    full["LAST_TRADED"] = grp["TRADED"].shift(1)

    lag_cols = ["PTS_36","AST_36","REB_36","STL_36","BLK_36","TOV_36",
                "USG_PCT","TS_PCT","PER","BPM","VORP","GP_PCT"]

    for col in lag_cols:
        if col in full.columns:
            full[f"LAST_{col}"]      = grp[col].shift(1)
            full[f"LAST_{col}_DIFF"] = grp[col].shift(1) - grp[col].shift(2)

    team_pred_cols = ["TEAM_ORTG","TEAM_DRTG","TEAM_PACE","TEAM_WIN_PCT",
                      "TEAM_TS_PCT","TEAM_SOS"]
    for col in team_pred_cols:
        if col in full.columns:
            full[f"LAST_{col}"]      = grp[col].shift(1)
            full[f"LAST_{col}_DIFF"] = grp[col].shift(1) - grp[col].shift(2)

    for col in ["PER","BPM","VORP"]:
        if col in full.columns:
            full[f"{col}_DIFF"] = full[col] - grp[col].shift(1)

    #Position dummies
    pos_map = {
        "PG":"Guard","SG":"Guard","G":"Guard",
        "SF":"Forward","PF":"Forward","F":"Forward","C":"Center",
        "G-F":"Guard-Forward","F-G":"Guard-Forward",
        "F-C":"Forward-Center","C-F":"Forward-Center",
    }
    if "POSITION" in full.columns:
        full["POSITION_CLEAN"] = full["POSITION"].map(pos_map).fillna("Forward")
        pos_dummies = pd.get_dummies(full["POSITION_CLEAN"], prefix="POS", drop_first=True)
        full = pd.concat([full, pos_dummies], axis=1)

    #Keep only rows where SEASON_NUM >= 3
    out_df = full[full["SEASON_NUM"] >= 3].copy()

    #Drop rows with missing team context
    team_required = ["LAST_TEAM_ORTG_DIFF", "LAST_TEAM_DRTG_DIFF"]
    team_required_present = [c for c in team_required if c in out_df.columns]
    if team_required_present:
        before = len(out_df)
        out_df = out_df.dropna(subset=team_required_present).copy()
        dropped = before - len(out_df)
        if dropped > 0:
            print(f"  Dropped {dropped} rows with missing LAST_TEAM_ORTG/DRTG_DIFF")

    #Select output columns
    personal    = ["PLAYER_NAME","SEASON","SEASON_NUM","AGE","LAST_TRADED",
                   "DRAFT_PROP","UNDRAFTED","GP_PCT","GP_ELIGIBLE"]
    pos_cols    = [c for c in out_df.columns if c.startswith("POS_")]
    player_last = [f"LAST_{c}" for c in
                   ["PTS_36","AST_36","REB_36","STL_36","BLK_36","TOV_36",
                    "USG_PCT","TS_PCT"] if f"LAST_{c}" in out_df.columns]
    player_mom  = [f"LAST_{c}_DIFF" for c in
                   ["PTS_36","AST_36","REB_36","STL_36","BLK_36","TOV_36",
                    "USG_PCT","TS_PCT"] if f"LAST_{c}_DIFF" in out_df.columns]
    team_last   = [f"LAST_{c}" for c in team_pred_cols if f"LAST_{c}" in out_df.columns]
    team_mom    = [f"LAST_{c}_DIFF" for c in team_pred_cols if f"LAST_{c}_DIFF" in out_df.columns]
    adv_pred    = ([f"LAST_{v}" for v in ["PER","BPM","VORP"] if f"LAST_{v}" in out_df.columns] +
                   [f"LAST_{v}_DIFF" for v in ["PER","BPM","VORP"] if f"LAST_{v}_DIFF" in out_df.columns])
    dep_vars    = [f"{v}_DIFF" for v in ["PER","BPM","VORP"] if f"{v}_DIFF" in out_df.columns]

    final_cols = (personal + pos_cols + player_last + player_mom +
                  team_last + team_mom + adv_pred + dep_vars)
    final_cols = [c for c in final_cols if c in out_df.columns]
    out = out_df[final_cols].copy()

    #Export to csv
    out.to_csv("nba_oos.csv", index=False)
    print(f"\n✓ Saved nba_oos.csv")
    print(f"  Seasons:        {sorted(out['SEASON'].unique())}")
    print(f"  Players:        {out['PLAYER_NAME'].nunique()}")
    print(f"  Rows (total):   {len(out)}")
    print(f"  GP_ELIGIBLE==1: {int(out['GP_ELIGIBLE'].sum())} rows "
          f"({out['GP_ELIGIBLE'].mean()*100:.1f}%)")
    print(f"  Traded last season: {int(out['LAST_TRADED'].sum())}")
    if "UNDRAFTED" in out.columns:
        print(f"  Undrafted players:  {int(out['UNDRAFTED'].sum())} rows")
    if "DRAFT_PROP" in out.columns:
        print(f"  Draft prop coverage:{out['DRAFT_PROP'].notna().mean()*100:.1f}%")
    print(f"\nTeam stat coverage (% non-null):")
    for col in ["LAST_TEAM_ORTG_DIFF","LAST_TEAM_DRTG_DIFF",
                "LAST_TEAM_PACE_DIFF","LAST_TEAM_TS_PCT_DIFF","LAST_TEAM_SOS_DIFF"]:
        if col in out.columns:
            print(f"  {col}: {out[col].notna().mean()*100:.1f}%")


if __name__ == "__main__":
    main()


