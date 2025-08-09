# MCP Server Design Specification

## Tools

The MCP server provides three tools for data retrieval. All analysis and draft recommendations are handled by the MCP client.

### 1. Draft Progress Tool
**Purpose**: Read current draft state from Google Sheets
- **Inputs**: None (uses configuration defaults)
- **Outputs**: Draft state object containing all picks and team/owner pairs
- **Implementation**:
  - Uses existing Google Sheets reading code (sheets_service.py works correctly)
  - Reads from Google Sheets specified in config.json
  - Expected sheet format: columns for team names, owners, and drafted players
  - Transform sheet data into simplified DraftState and DraftPick objects
  - On error: Retry once, then return error for MCP client to handle
  - No caching needed (draft state changes frequently)

### 2. Player Rankings Tool  
**Purpose**: Retrieve player rankings by position
- **Inputs**: 
  - position: Required string ("QB", "RB", "WR", "TE", "K", "DST")
- **Outputs**: List of player objects with ranking data for that position
- **Implementation**:
  - Data source: FantasySharks only (existing scraper implementation works)
  - Caching: In-memory cache, populated on first request for each position
  - Cache lifetime: Duration of MCP server session (refreshes on restart)
  - If position data already cached: Return from memory
  - If not cached: Scrape from FantasySharks, store in memory, return
  - On scraping error: Retry once, then return error
  - Token limit management: Position parameter is required to limit response size

### 3. Player Info Tool
**Purpose**: Get detailed information about a specific player
- **Inputs**:
  - last_name: Required string
  - first_name: Optional string  
  - team: Optional string (NFL team abbreviation)
  - position: Optional string
- **Outputs**: Single player object or list of matching players
- **Implementation**:
  - Search in-memory rankings cache first
  - If player not found and position provided: Call rankings tool for that position
  - If player not found and no position: Return error (avoid loading all positions)
  - Return all matching players based on search criteria

### 4. Available Players Tool
**Purpose**: Get a list of top undrafted players at a position
- **Inputs**:
  - position: Required string ("QB", "RB", "WR", "TE", "K", "DST")
  - limit: Required integer (max number of players to return)
- **Outputs**: List of undrafted Player objects with complete ranking data
- **Implementation**:
  - Internally fetches current draft state from Google Sheets (with caching)
  - Internally calls Player Rankings tool if position not cached
  - Get cached rankings for the specified position
  - Filter out players already in draft_state.picks
  - Sort remaining players by projected_points (descending)
  - Return top <limit> available players with all player data 


## Data Models

### 1. DraftState
Represents the current state of the draft.
```python
class DraftState:
    - picks: List[DraftPick]  # All picks made so far
    - teams: List[Dict]       # Team/owner pairs: [{"owner": str, "team_name": str}]
```
Note: Team rosters can be derived from picks list when needed. No need for separate roster tracking.

### 2. DraftPick
Represents a single draft pick.
```python
class DraftPick:
    - player: Player          # The drafted player
    - owner: str              # Fantasy owner who drafted them
```
Note: Round/pick numbers and timestamps are not needed for this implementation.

### 3. Player
Core player information with ranking data.
```python
class Player:
    - name: str               # Full player name
    - team: str               # NFL team abbreviation
    - position: str           # Position (QB, RB, WR, TE, K, DST)
    - bye_week: int           # Bye week number
    - injury_status: InjuryStatus  # Enum for injury states
    - ranking: int            # FantasySharks ranking
    - projected_points: float # Projected fantasy points
    - notes: str              # Additional notes/analysis from source
```

### 4. InjuryStatus
Enum for tracking player health.
```python
class InjuryStatus(Enum):
    HEALTHY = "HEALTHY"
    QUESTIONABLE = "Q"
    DOUBTFUL = "D"
    OUT = "O"
    INJURED_RESERVE = "IR"
```

### 5. PlayerRankings
Container for cached rankings data.
```python
class PlayerRankings:
    - position_data: Dict[str, List[Player]]  # Cached by position
    - last_updated: Dict[str, datetime]       # Track cache age by position
```

## Responsibilities Division

### MCP Server (This Implementation)
- **Data retrieval only**: Google Sheets, web scraping
- **Simple caching**: In-memory storage for rankings
- **Error handling**: Retry logic, error reporting
- **No analysis**: Just return raw data

### MCP Client (External)
- **All analysis logic**: Team needs, positional scarcity, bye week stacking
- **Draft strategy**: Best available, position targeting, value calculations
- **Recommendations**: Suggest picks based on analysis
- **User interaction**: Interpret user intent, format responses

## Implementation Guidelines

### Existing Code to Preserve
- **Google Sheets reading**: The current sheets_service.py implementation works correctly
- **FantasySharks scraper**: The existing FantasySharksScraper class functions properly
- Focus refactoring on data transformation and model simplification, not data retrieval

### Test-Driven Development
1. Write test first for each new feature
2. Implement minimal code to pass test
3. Refactor for clarity while keeping tests green
4. Each module should have corresponding test file in tests/

### Error Handling Strategy
```python
def fetch_with_retry(func, max_retries=1):
    try:
        return func()
    except Exception as e:
        if max_retries > 0:
            return fetch_with_retry(func, max_retries - 1)
        return {"success": False, "error": str(e)}
```

### Caching Implementation

#### Rankings Cache
```python
# Global in-memory cache for rankings (persistent for server session)
_rankings_cache = {
    "QB": None,
    "RB": None,
    "WR": None,
    "TE": None,
    "K": None,
    "DST": None
}

def get_cached_or_fetch(position):
    if _rankings_cache[position] is not None:
        return _rankings_cache[position]
    
    data = scrape_fantasysharks(position)
    _rankings_cache[position] = data
    return data
```

#### Draft State Cache
```python
# TTL-based cache for draft state (configurable expiration)
from cachetools import TTLCache
from datetime import timedelta

# Cache with configurable TTL from config
_draft_state_cache = TTLCache(
    maxsize=1,  # Only cache the latest draft state
    ttl=DRAFT_STATE_CACHE_TTL_SECONDS  # From config.py
)

async def get_cached_draft_state(sheet_id, sheet_range):
    cache_key = f"{sheet_id}:{sheet_range}"
    
    if cache_key in _draft_state_cache:
        return _draft_state_cache[cache_key]
    
    # Fetch fresh from Google Sheets
    draft_state = await read_draft_progress(sheet_id, sheet_range)
    _draft_state_cache[cache_key] = draft_state
    return draft_state
```

### Configuration
All settings in config.json:
- Google Sheets ID and range
- Owner name mapping
- Retry counts
- Draft state cache TTL (seconds, default: 60)
- Any other deployment-specific settings

## Key Design Decisions

1. **No persistence**: Cache lives in memory only, refreshes on restart
2. **Single data source**: FantasySharks only for simplicity and reliability
3. **Position-based caching**: Avoids token limits, improves performance
4. **Draft state caching**: TTL-based cache (default 60s) to reduce Google Sheets API calls
5. **Minimal objects**: Only essential fields, no computed properties
6. **Clear separation**: Server provides data, client provides intelligence
7. **Internal tool chaining**: Available Players tool internally fetches draft state and rankings as needed

## MCP Client Usage Example

**User Question**: "Which 5 QBs should I be targeting at this point in the draft?"

**MCP Client Actions**:
1. Call Available Players Tool with:
   - position: "QB"  
   - limit: 10 (get extras for analysis)
2. Receive list of available QBs with rankings/projections and draft context
3. Use AI to analyze based on:
   - Draft context included in response (teams, picks made)
   - Draft strategy (from client's system prompt)
   - Player data (from available players)
4. Return recommendation of top 5 QBs with reasoning

**Note**: Client only needs 1 tool call. The server handles both draft state and rankings internally.