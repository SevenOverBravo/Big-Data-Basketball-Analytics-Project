## Variable Descriptions

### Player Background
| Variable | Type | Description |
|---|---|---|
| `AGE` | Float | Player age at time of trade/signing |
| `LAST_TRADED` | Binary | Indicator for whether player was traded in their last season |
| `DRAFT_PROP` | Float | Draft position percentile or draft probability proxy |
| `UNDRAFTED` | Binary | Indicator for whether player went undrafted |
| `GP_PCT` | Float | Percentage of team games played last season |
| `POS_Forward` | Binary | Indicator for forward position |
| `POS_Guard` | Binary | Indicator for guard position |

### Last Season Per-36 Stats
| Variable | Type | Description |
|---|---|---|
| `LAST_PTS_36` | Float | Points per 36 minutes, last season |
| `LAST_AST_36` | Float | Assists per 36 minutes, last season |
| `LAST_REB_36` | Float | Rebounds per 36 minutes, last season |
| `LAST_STL_36` | Float | Steals per 36 minutes, last season |
| `LAST_BLK_36` | Float | Blocks per 36 minutes, last season |
| `LAST_TOV_36` | Float | Turnovers per 36 minutes, last season |
| `LAST_USG_PCT` | Float | Usage percentage, last season |
| `LAST_TS_PCT` | Float | True shooting percentage, last season |

### Last Season Per-36 Year-Over-Year Changes
| Variable | Type | Description |
|---|---|---|
| `LAST_PTS_36_DIFF` | Float | Change in points per 36 from previous season |
| `LAST_AST_36_DIFF` | Float | Change in assists per 36 from previous season |
| `LAST_REB_36_DIFF` | Float | Change in rebounds per 36 from previous season |
| `LAST_STL_36_DIFF` | Float | Change in steals per 36 from previous season |
| `LAST_BLK_36_DIFF` | Float | Change in blocks per 36 from previous season |
| `LAST_TOV_36_DIFF` | Float | Change in turnovers per 36 from previous season |
| `LAST_USG_PCT_DIFF` | Float | Change in usage percentage from previous season |
| `LAST_TS_PCT_DIFF` | Float | Change in true shooting percentage from previous season |

### Last Season Team Context
| Variable | Type | Description |
|---|---|---|
| `LAST_TEAM_ORTG` | Float | Offensive rating of player's last team |
| `LAST_TEAM_DRTG` | Float | Defensive rating of player's last team |
| `LAST_TEAM_WIN_PCT` | Float | Win percentage of player's last team |
| `LAST_TEAM_ORTG_DIFF` | Float | Change in team offensive rating from previous season |
| `LAST_TEAM_DRTG_DIFF` | Float | Change in team defensive rating from previous season |
| `LAST_TEAM_WIN_PCT_DIFF` | Float | Change in team win percentage from previous season |

### Last Season Advanced Stats
| Variable | Type | Description |
|---|---|---|
| `LAST_PER` | Float | Player Efficiency Rating, last season |
| `LAST_BPM` | Float | Box Plus/Minus, last season |
| `LAST_VORP` | Float | Value Over Replacement Player, last season |
| `LAST_PER_DIFF` | Float | Change in PER from previous season |
| `LAST_BPM_DIFF` | Float | Change in BPM from previous season |
| `LAST_VORP_DIFF` | Float | Change in VORP from previous season |

### Outcome Variables
| Variable | Type | Description |
|---|---|---|
| `PER_DIFF` | Float | Change in PER from last season to contract season |
| `BPM_DIFF` | Float | Change in BPM from last season to contract season |
| `VORP_DIFF` | Float | Change in VORP from last season to contract season |
