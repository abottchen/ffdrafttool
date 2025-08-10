# MCP Server Design Specification

## Tools

The MCP server provides five tools for data retrieval. All analysis and draft recommendations are handled by the MCP client.

### 1. Draft Progress Tool
**Purpose**: Read current draft state from Google Sheets
- **Inputs**: 
  - force_refresh: Optional boolean (default: false) to bypass cache
- **Outputs**: Draft state object containing all picks and team/owner pairs
- **Implementation**:
  - Uses configuration-driven sheet selection (sheet_id and range from config.json)
  - Format-aware parsing based on draft.format configuration setting
  - Transform sheet data into simplified DraftState and DraftPick objects using appropriate parser
  - TTL-based caching for draft state with configurable cache duration
  - On error: Retry once, then return error for MCP client to handle

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

### 5. Team Roster Tool
**Purpose**: Get all drafted players for a specific owner
- **Inputs**:
  - owner_name: Required string (exact owner name from draft data)
- **Outputs**: List of Player objects for that owner
- **Implementation**:
  - Internally fetches current draft state from Google Sheets (with caching)
  - Filter all picks by matching owner name (case-insensitive)
  - Return list of Player objects from matching DraftPick entries
  - Warms draft state cache for subsequent available_players calls
  - Provides team context needed for MCP client recommendations


## Data Models

### 1. DraftState
Represents the current state of the draft.
- **picks**: List of all draft picks made so far
- **teams**: List of team/owner pairs with owner name and team name

Note: Team rosters can be derived from picks list when needed. No need for separate roster tracking.

### 2. DraftPick
Represents a single draft pick.
- **player**: The drafted player object
- **owner**: Fantasy owner who drafted them

Note: Round/pick numbers and timestamps are not needed for this implementation.

### 3. Player
Core player information with ranking data.
- **name**: Full player name
- **team**: NFL team abbreviation
- **position**: Position (QB, RB, WR, TE, K, DST)
- **bye_week**: Bye week number
- **injury_status**: Enum for injury states
- **ranking**: FantasySharks ranking
- **projected_points**: Projected fantasy points
- **notes**: Additional notes/analysis from source

### 4. InjuryStatus
Enumeration for tracking player health status.
- HEALTHY: Player is healthy
- QUESTIONABLE: Listed as questionable (Q)
- DOUBTFUL: Listed as doubtful (D)
- OUT: Listed as out (O)
- INJURED_RESERVE: On injured reserve (IR)

### 5. PlayerRankings
Container for cached rankings data.
- **position_data**: Dictionary mapping positions to lists of players
- **last_updated**: Dictionary tracking cache age by position

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

### Caching Strategy

#### Rankings Cache
- Global in-memory cache for rankings data, persists for server session duration
- Cache organized by position (QB, RB, WR, TE, K, DST)
- On cache miss: Fetch from FantasySharks, store in memory, return data
- On cache hit: Return immediately from memory
- No expiration within session - rankings assumed stable during draft

#### Draft State Cache  
- TTL-based cache using cachetools library for automatic expiration
- Single entry cache (only latest draft state stored)
- Configurable TTL from configuration file (default: 60 seconds)
- Cache key generated from sheet_id and sheet_range (format-aware)
- Configuration automatically determines sheet parameters based on draft format
- On cache miss: Fetch fresh from Google Sheets using appropriate parser
- On cache hit: Return cached draft state if within TTL window

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
1. Call Team Roster Tool with:
   - owner_name: "Adam" (from user configuration)
2. Receive user's current roster composition
3. Call Available Players Tool with:
   - position: "QB"  
   - limit: 10 (get extras for analysis)
4. Use AI to analyze based on:
   - Current team needs (from roster composition)
   - Draft strategy (from client's system prompt)
   - Available player data (rankings, projections)
5. Return recommendation of top 5 QBs with reasoning

**Note**: Team Roster Tool warms the draft state cache, making Available Players Tool calls fast.

## Dual Draft Format Support Architecture

### Overview
The MCP server supports two different Google Sheets draft formats through a pluggable parser architecture:
- **Dan Format**: Snake draft with team abbreviations included in player names
- **Adam Format**: Auction draft with "last, first" names and no team abbreviations

### Architecture Design

#### Strategy Pattern Implementation
```
src/services/
├── sheet_parser.py           # Abstract base class defining parse interface
├── dan_draft_parser.py       # Handles current "Draft" sheet format
├── adam_draft_parser.py      # Handles "Adam" sheet auction format  
└── sheets_service.py         # Strategy context, selects parser based on config
```

#### Parser Interface
Each parser implements a standard interface:
- **Parse Method**: Converts raw sheet data to `DraftState` objects
- **Format Detection**: Validates sheet structure matches expected format
- **Error Handling**: Graceful handling of malformed or missing data
- **Rankings Integration**: Optional rankings cache for team/position lookup

### Draft Format Specifications

#### Dan Format (Current Implementation)
- **Sheet Name**: "Draft"
- **Draft Type**: Snake draft
- **Player Format**: "Josh Allen (BUF)" - includes team abbreviations
- **Team Names**: Embedded in sheet cells
- **Roster Balance**: Equal rounds, balanced rosters
- **Owner Information**: Explicit team names and owners in sheet

#### Adam Format (New Implementation)  
- **Sheet Name**: "Adam"
- **Draft Type**: Auction draft
- **Player Format**: "Hall, Breece" - last name first, no team info
- **Team Names**: Must be looked up from rankings cache
- **Roster Balance**: Unequal rosters, gaps allowed (auction style)
- **Owner Information**: Names in header row only
- **Defense Format**: "Ravens D/ST" - full team name + D/ST
- **Special Handling**: Skip $ value columns, reverse name format

### Configuration

#### Required Configuration
The configuration file must specify:
- **draft.format**: Set to "dan" or "adam" to select the parser
- **draft.sheet_id**: Google Sheet ID (same for both formats)
- **draft.formats.dan**: Configuration for Dan format including sheet name and range
- **draft.formats.adam**: Configuration for Adam format including sheet name and range

Each format configuration includes:
- **sheet_name**: Name of the sheet tab
- **sheet_range**: Cell range to read (e.g., "Draft!A1:V24" or "Adam!A1:T20")

#### Format Selection
The factory pattern selects the appropriate parser based on configuration:
- **Dan Format**: Uses `DanDraftParser` for snake drafts
- **Adam Format**: Uses `AdamDraftParser` with rankings cache for auction drafts
- **Configuration Driven**: Format selection based on `draft.format` setting


### Data Flow
1. **Configuration** determines which format parser to use
2. **Sheets Service** fetches raw data from Google Sheets
3. **Format Parser** converts sheet data to standardized `DraftState`
4. **MCP Tools** receive identical `DraftState` regardless of source format

This abstraction ensures all tools work with both draft formats without modification.

### Validation & Error Handling
- **Format Detection**: Parsers validate sheet structure matches expected format
- **Configuration Validation**: Ensure format is specified, sheet configuration exists
- **Runtime Validation**: Detect format mismatches between config and actual sheet data
- **Graceful Degradation**: Handle missing players, team lookup failures

### Benefits
1. **Zero Impact on MCP Tools**: All tools continue to work with DraftState objects
2. **Clean Separation**: Format-specific logic isolated in parser classes  
3. **Extensible**: Easy to add new draft formats in the future
4. **Testable**: Each parser can be unit tested independently
5. **Configurable**: Switch formats without code changes

### Future Enhancements

#### DanDraftParser Simplification (Future)
The current `DanDraftParser` uses a complex row-based approach that:
- Iterates through rows and extracts picks for each team column
- Uses snake draft logic to determine "correct" team ownership  
- Rebuilds team structures multiple times

**Opportunity**: Simplify to column-based approach since Google Sheets draft format is naturally columnar:
- Column 0: Round numbers
- Column 1,2: Team 1 (Player, Position)
- Column 3,4: Team 2 (Player, Position) 
- etc.

This would eliminate the need for complex pick ordering logic since each team's picks are already in chronological order within their column. However, this refactoring is deferred to avoid functional changes in Phase 1.