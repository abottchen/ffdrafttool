# Fantasy Football Draft Assistant MCP Server

A Model Context Protocol (MCP) server that provides fantasy football data to any MCP client for intelligent draft assistance. This server follows a **data-only architecture** - it retrieves and caches data from various sources, while the MCP client performs all analysis and recommendations.

## Architecture Overview

This MCP server implements a clean separation of concerns:
- **MCP Server (this repository)**: Provides raw data through 5 simple tools
- **MCP Client (e.g., Claude, GPT, etc.)**: Performs all analysis, strategy, and recommendations

## Supported Draft Formats

The server supports multiple draft data sources through a pluggable parser architecture:

- **Dan Format**: Snake draft from Google Sheets with team abbreviations in player names (`"Josh Allen BUF"`)
- **Adam Format**: Auction draft from Google Sheets with "Last, First" names and team lookup (`"Hall, Breece"`)
- **Tracker Format**: Real-time draft data from HTTP API endpoints (no Google Sheets required)

Switch between formats by updating the `draft.format` setting in your configuration.

## Features

- **Multi-source player rankings** - Retrieves data from FantasySharks web scraping
- **Real-time draft tracking** - Reads draft progress from Google Sheets
- **Player information search** - Finds specific players by name, team, or position
- **Available players filtering** - Lists undrafted players at each position
- **Efficient caching** - In-memory caching for optimal performance
- **Simple data models** - Lightweight, focused data structures

## Data Sources

The server currently retrieves data from:
- **FantasySharks**: Player rankings via web scraping (no API key required)
- **Google Sheets**: Live draft tracking data for Dan/Adam formats (requires Google API credentials)
- **HTTP API**: Real-time draft tracking for Tracker format (requires API server at localhost:8175)

Future versions may add additional sources like ESPN, Yahoo, and FantasyPros.

## Installation

1. **Clone and install dependencies**:
   ```bash
   cd fantasy-football-draft-assistant
   pip install -e ".[dev]"
   ```

2. **Configure the application**:
   ```bash
   cp config.json.example config.json
   ```
   Edit `config.json` with your settings:
   - `draft.format`: Set to "dan" (snake draft), "adam" (auction draft), or "tracker" (API-based)
   - `draft.owner_name`: Your name as it appears in the draft data
   
   **For Google Sheets formats (Dan/Adam)**:
   - `google_sheets.default_sheet_id`: Your Google Sheet ID for draft tracking
   - Configure sheet ranges for each format in `draft.formats` section
   
   **For Tracker format**:
   - `draft.formats.tracker.base_url`: API endpoint (default: http://localhost:8175)
   - No Google Sheets configuration needed
   
   - Cache settings can be left as defaults

3. **Set up Google Sheets API** (for Dan/Adam formats only):
   - Create credentials at [Google Cloud Console](https://console.developers.google.com/)
   - Download `credentials.json` to the project directory
   - Run the authentication flow when first using Google Sheets features
   - Not required for Tracker format

   **Optional environment variables:**
   - `GOOGLE_CREDENTIALS_FILE`: Custom path to credentials.json (defaults to project root)
   - `GOOGLE_TOKEN_FILE`: Custom path to token.json (defaults to project root)

## Using with MCP Clients

This server can be used with any MCP-compatible client. For LLM-based clients (Claude, GPT, etc.), we provide an example prompt configuration in `example-prompt.md` that enables the client to:
- Analyze player value and rankings
- Generate draft recommendations based on team needs
- Consider positional scarcity and bye weeks
- Provide personalized advice based on draft strategy

### For Claude Code Users
Copy `example-prompt.md` to your project root as `CLAUDE.md` to enable intelligent draft analysis.

### For Other MCP Clients
Adapt the prompt in `example-prompt.md` to your client's configuration format. The prompt contains domain knowledge about fantasy football strategy that helps LLMs provide better recommendations.

## Testing

Run the test suite:
```bash
pytest
```

## Available MCP Tools

The server provides 5 data-retrieval tools. All analysis and recommendations are performed by the MCP client.

### 1. `get_player_rankings`
Retrieves player rankings from FantasySharks with caching.

**Parameters:**
- `position_filter` (optional): Filter by position (QB, RB, WR, TE, K, DST, or null for all)
- `force_refresh` (default: false): Bypass cache and fetch fresh data

**Returns:** List of players with rankings and basic information

### 2. `read_draft_progress`
Reads current draft state from configured data source with format-aware parsing.

**Parameters:**
- `force_refresh` (default: false): Ignore cache and fetch fresh data

**Returns:** Draft state with picks made and team rosters

**Note:** Data source is automatically determined from configuration based on the selected draft format:
- **Dan/Adam formats**: Reads from Google Sheets with appropriate parser
- **Tracker format**: Fetches from HTTP API endpoints (localhost:8175)

### 3. `get_available_players`
Lists top undrafted players at a specific position.

**Parameters:**
- `position` (required): Position to filter (QB, RB, WR, TE, K, DST)
- `limit` (default: 10): Maximum number of players to return

**Returns:** List of available players at the specified position

**Note:** This tool automatically fetches current draft state internally with caching.

### 4. `get_team_roster`
Gets all drafted players for a specific owner.

**Parameters:**
- `owner_name` (required): Name of the team owner as it appears in draft data

**Returns:** List of Player objects for that owner's team

**Note:** This tool warms the draft state cache and should typically be called first for personalized recommendations.

### 5. `get_player_info`
Searches for specific players by name.

**Parameters:**
- `last_name` (required): Player's last name (handles partial matches)
- `first_name` (optional): Player's first name to narrow results
- `team` (optional): Team abbreviation filter
- `position` (optional): Position filter

**Returns:** Matching players with their information

## Usage Examples

When used with an LLM-based MCP client configured with the example prompt, you can ask questions like:

### Draft Assistance
```
"Who should I draft next?"
"Show me the best available running backs"
"What positions does my team still need?"
"Tell me about Patrick Mahomes"
```

### How It Works

1. **You ask your MCP client** for draft advice
2. **The MCP client calls server tools** to get data:
   - `read_draft_progress` to get current draft state and picks (format-aware)
   - `get_team_roster` to see your current team composition
   - `get_available_players` to see undrafted players by position
   - `get_player_rankings` to get comprehensive player data
   - `get_player_info` to look up specific players
3. **The MCP client analyzes** the data considering:
   - Your roster needs
   - Positional scarcity
   - Player value and rankings
   - Bye week conflicts
4. **The MCP client provides** intelligent recommendations

## Performance Features

- **In-memory caching** for player rankings (reduces web scraping)
- **Draft state caching** with TTL (avoids redundant Google Sheets reads)  
- **Simplified data models** (minimal data transfer)
- **Fast response times** (data-only, no complex analysis)

## Project Structure

```
.
├── src/
│   ├── config.py                    # Configuration settings
│   ├── server.py                    # Main MCP server with 5 tools
│   ├── tools/
│   │   ├── player_rankings.py       # Get player rankings tool
│   │   ├── draft_progress.py        # Read draft progress tool
│   │   ├── available_players.py     # Get available players tool
│   │   ├── team_roster.py           # Get team roster tool
│   │   └── player_info.py           # Get player info tool
│   ├── models/
│   │   ├── player_simple.py         # Simplified Player model
│   │   ├── draft_state_simple.py    # Simplified DraftState model
│   │   └── draft_pick.py            # DraftPick model
│   └── services/
│       ├── sheet_parser.py          # Abstract parser interface
│       ├── dan_draft_parser.py      # Dan format parser (snake draft)
│       ├── adam_draft_parser.py     # Adam format parser (auction draft)
│       ├── tracker_draft_parser.py  # Tracker format parser (API-based)
│       ├── tracker_api_service.py   # HTTP client for tracker API
│       ├── sheets_service.py        # Google Sheets integration & parser factory
│       ├── web_scraper.py           # FantasySharks scraper
│       ├── draft_state_cache.py     # TTL-based caching for draft data
│       └── team_mapping.py          # Team abbreviation normalization
├── tests/                           # Comprehensive test suite
├── example-prompt.md                # Example prompt for LLM-based MCP clients
├── run_server.py                    # Server entry point
└── README.md                        # This file
```

## Design Philosophy

This MCP server follows the principle of **separation of concerns**:

1. **Data Layer (MCP Server)**: Focuses solely on data retrieval and caching
2. **Analysis Layer (MCP Client)**: Performs all intelligent analysis and recommendations
3. **Simplified Models**: Uses Pydantic models for type safety and validation
4. **Clean Architecture**: Web scrapers directly create domain models without conversion

This design makes the server:
- **Client-agnostic**: Works with any MCP-compatible client
- **Maintainable**: Clear separation between data and logic
- **Testable**: Simple interfaces with predictable outputs
- **Efficient**: Minimal data transfer and processing

The example prompt (`example-prompt.md`) provides domain knowledge that enables LLM-based clients to deliver sophisticated fantasy football analysis.
