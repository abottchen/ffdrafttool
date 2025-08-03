# Fantasy Football Draft Assistant MCP Server

A Model Context Protocol (MCP) server that provides real-time fantasy football draft assistance by analyzing player rankings, draft progress from Google Sheets, and generating intelligent draft recommendations.

## 🏈 Features

- **Multi-source player rankings** - Aggregates data from FantasySharks, ESPN, Yahoo, and FantasyPros
- **Real-time draft tracking** - Integrates with Google Sheets to track live draft progress
- **Intelligent recommendations** - AI-powered draft pick suggestions based on roster needs and strategy
- **Value analysis** - Advanced metrics including positional scarcity and player value scores
- **Bye week optimization** - Avoids creating roster conflicts during bye weeks
- **Personalized assistance** - Recognizes "I/me/my team" references for personalized recommendations
- **Caching system** - Optimized performance with in-memory caching
- **Multiple draft formats** - Supports auction, keeper, and snake draft formats

## 📊 Data Sources

This tool aggregates data from publicly accessible fantasy football websites:
- **FantasySharks**: Expert rankings and analysis
- **ESPN Fantasy Football**: Player rankings and projections  
- **Yahoo Fantasy Sports**: Rankings and draft analysis
- **FantasyPros**: Consensus rankings from multiple experts

No API keys are required - all data is gathered from public web pages.

## 🛠️ Installation

1. **Clone and install dependencies**:
   ```bash
   cd C:\Users\adam\Documents\Projects\ffdrafttool2
   pip install -e ".[dev]"
   ```

2. **Configure the application**:
   ```bash
   cp config.json.example config.json
   ```
   Edit `config.json` with your settings:
   - `google_sheets.default_sheet_id`: Your Google Sheet ID for draft tracking
   - `draft.owner_name`: Your name as it appears in the draft data
   - Cache settings can be left as defaults

3. **Set up Google Sheets API** (for draft tracking):
   - Create credentials at [Google Cloud Console](https://console.developers.google.com/)
   - Download `credentials.json` to the project directory
   - Run the authentication flow when first using Google Sheets features

   **Optional environment variables:**
   - `GOOGLE_CREDENTIALS_FILE`: Custom path to credentials.json (defaults to project root)
   - `GOOGLE_TOKEN_FILE`: Custom path to token.json (defaults to project root)

## 👤 Owner Configuration

The assistant can be personalized to recognize first-person references ("I", "me", "my team") as referring to your team.

## 🧪 Testing

Run the test suite:
```bash
pytest
```

## 🔧 Available MCP Tools

The server provides the following MCP tools for fantasy football draft assistance:

### 1. `get_player_rankings_tool`
Fetch current player rankings from multiple fantasy football sources.

**Parameters:**
- `position` (optional): Filter by position (QB, RB, WR, TE, K, DST)
- `limit` (default: 20): Number of players to return per page
- `offset` (default: 0): Starting position for pagination
- `force_refresh` (default: false): Bypass cache and fetch fresh data

**Usage:**
- Get top 20 players: `get_player_rankings_tool()`
- Get top 10 QBs: `get_player_rankings_tool(position="QB", limit=10)`
- Get RBs 21-40: `get_player_rankings_tool(position="RB", limit=20, offset=20)`

### 2. `read_draft_progress_tool`
Read live draft progress from Google Sheets.

**Parameters:**
- `sheet_id` (optional): Google Sheets ID (uses configured default if not provided)
- `sheet_range` (default: "Draft!A1:V24"): Range to read from the sheet
- `force_refresh` (default: false): Ignore cache and fetch fresh data

**Usage:**
- Read current draft state: `read_draft_progress_tool()`
- Read from specific sheet: `read_draft_progress_tool(sheet_id="your_sheet_id")`

### 3. `analyze_available_players_tool`
Analyze available players with value metrics, positional scarcity, and bye week considerations.

**Parameters:**
- `draft_state` (required): Current draft state from `read_draft_progress_tool`
- `position_filter` (optional): Focus on specific position (QB, RB, WR, TE, K, DST)
- `limit` (default: 20): Number of players to analyze and return
- `force_refresh` (default: false): Fetch fresh rankings data

**Usage:**
- Analyze top available players: `analyze_available_players_tool(draft_state)`
- Focus on available RBs: `analyze_available_players_tool(draft_state, position_filter="RB")`

### 4. `suggest_draft_pick_tool`
Get personalized draft pick recommendations based on team needs and strategy.

**Parameters:**
- `draft_state` (required): Current draft state from `read_draft_progress_tool`
- `strategy` (default: "balanced"): Draft strategy - "balanced", "best_available", "upside", "safe"
- `consider_bye_weeks` (default: true): Factor in bye week conflicts
- `force_refresh` (default: false): Use fresh rankings data

**Usage:**
- Get balanced recommendation: `suggest_draft_pick_tool(draft_state)`
- Use upside strategy: `suggest_draft_pick_tool(draft_state, strategy="upside")`
- Ignore bye weeks: `suggest_draft_pick_tool(draft_state, consider_bye_weeks=false)`

### 5. `get_player_info_tool`
Get detailed information about specific players by name.

**Parameters:**
- `last_name` (required): Player's last name (handles partial matches and suffixes)
- `first_name` (optional): Player's first name to narrow results
- `team` (optional): Team abbreviation filter (e.g., "KC", "SF")
- `position` (optional): Position filter (QB, RB, WR, TE, K, DST)

**Usage:**
- Find player by last name: `get_player_info_tool(last_name="Mahomes")`
- Handle suffixes: `get_player_info_tool(last_name="Penix")` (finds "Michael Penix Jr.")
- Narrow by first name: `get_player_info_tool(first_name="Patrick", last_name="Mahomes")`
- Filter by team: `get_player_info_tool(last_name="Williams", team="NYJ")`

## 💡 Usage Examples

### Basic Draft Assistance
```
Who should I pick next?
Show me the best available quarterbacks
What positions do I still need to fill?
What do you know about Patrick Mahomes?
Tell me about Penix (finds Michael Penix Jr.)
```

### Advanced Analysis
```
First, read my draft progress from the Google Sheet. Then analyze the top 20 available players and suggest my next pick using an upside strategy, considering bye weeks.
```

### Multi-Step Workflow
```
1. Get current player rankings for RBs
2. Read my draft state  
3. Analyze available RBs based on my team needs
4. Suggest the best RB pick using safe strategy
```

### Pagination Examples
```
Get the top 20 quarterbacks (page 1)
Get quarterbacks ranked 21-40 using offset=20
Get the next page of running backs
Show me 10 wide receivers starting from rank 31
```

## 🏆 Performance Features

- **In-memory caching** for player rankings (reduces API calls)
- **Draft state caching** (avoids redundant Google Sheets reads)  
- **Token optimization** (responses under 25k tokens for faster processing)
- **Incremental updates** (only processes new draft picks)

## 📁 Project Structure

```
ffdrafttool/
├── src/
│   ├── config.py              # Configuration settings
│   ├── server.py              # Main MCP server
│   ├── tools/
│   │   ├── mcp_tools.py       # Core MCP tool implementations
│   │   ├── rankings_cache.py  # Player rankings caching
│   │   └── web_scraper.py     # Data collection from sources
│   ├── models/                # Data models
│   └── services/              # Business logic services
├── tests/                     # Comprehensive test suite
├── run_server.py             # Server entry point
└── README.md                 # This file
```
