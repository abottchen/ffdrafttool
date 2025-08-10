# Fantasy Football Draft Assistant MCP Server

This is a **data-only** MCP server that provides fantasy football information through 5 simple tools. The server retrieves and caches data, while all analysis and recommendations are performed by the MCP client.

## Architecture Overview

**Simplified Design (as per DESIGN.md):**
- **MCP Server**: Provides raw data only (rankings, draft state, player info)
- **MCP Client**: Performs all analysis and strategy (see `example-prompt.md`)
- **Clean Separation**: No analysis logic in server code

## Development Commands

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

Lint code:
```bash
ruff check src/ tests/
```

Format code:
```bash
black src/ tests/
```

Start MCP server:
```bash
python run_server.py
```

## Project Structure

```
./
├── src/
│   ├── server.py                    # FastMCP server with 5 tool endpoints
│   ├── tools/                       # MCP tool implementations
│   │   ├── draft_progress.py        # Reads Google Sheets draft data
│   │   ├── player_rankings.py       # Gets rankings with caching
│   │   ├── player_info.py           # Searches for specific players
│   │   ├── available_players.py     # Filters undrafted players
│   │   └── team_roster.py           # Gets team roster for owner
│   ├── models/                      # Simplified data models
│   │   ├── player_simple.py         # Basic player with rankings
│   │   ├── draft_state_simple.py    # Draft state (picks + teams)
│   │   ├── draft_pick.py            # Single pick (player + owner)
│   │   └── injury_status.py         # Injury status enum
│   └── services/                    # Data retrieval layer
│       ├── sheets_service.py        # Google Sheets API integration
│       ├── web_scraper.py           # FantasySharks scraper
│       ├── team_mapping.py          # Team abbreviation normalization
│       └── draft_state_cache.py     # Draft state caching
├── tests/                           # Comprehensive test suite
├── DESIGN.md                        # Architecture specification
├── example-prompt.md                # LLM client configuration
└── config.json                      # Server configuration
```

## Available MCP Tools

1. **`get_player_rankings`** - Retrieves cached rankings by position
2. **`read_draft_progress`** - Reads current draft from Google Sheets  
3. **`get_available_players`** - Lists undrafted players at position
4. **`get_team_roster`** - Gets all drafted players for a specific owner
5. **`get_player_info`** - Searches for specific player details

## Development Guidelines

### Core Principles
- **Data Only**: Server provides data, client provides intelligence
- **No Analysis**: Remove any code that analyzes, recommends, or strategizes
- **Simple Models**: Use minimal data structures (see `src/models/`)
- **Direct Model Creation**: Scrapers create Pydantic models directly

### Coding Standards
- **Type Hints**: All functions must have type annotations
- **Error Handling**: Retry once, then return error for client to handle
- **Testing**: Write tests first (TDD), maintain >60% coverage
- **Linting**: Run `ruff check` before committing

### Configuration
- All settings in `config.json` (never hardcode)
- Google Sheets ID and range configurable
- Cache behavior configurable

### Caching Strategy
- In-memory only (no persistence)
- Cache by position for rankings
- Cache lifetime = server session
- No caching for draft state (changes frequently)

## Testing

### Test Organization
- `tests/models/` - Data model tests
- `tests/services/` - Service layer tests  
- `tests/tools/` - MCP tool tests
- `tests/fixtures/` - Test data and mocks

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test groups
pytest tests/models/
pytest tests/services/
pytest tests/tools/

# Run specific test file
pytest tests/tools/test_draft_progress.py -v
```

## Current Implementation Status

### ✅ Completed
- Implements 5 focused data-only tools
- Server provides data only, no analysis logic
- Direct Pydantic model creation in scrapers and sheets service
- Comprehensive test suite with good coverage
- Full conformance with DESIGN.md specification

### ⚠️ Known Limitations  
- Only FantasySharks scraper implemented (ESPN, Yahoo, FantasyPros are stubs)
- Data sources limited to FantasySharks for rankings (other scrapers are planned)
- Some integration opportunities remain for additional data sources

### 📝 Future Enhancements (per DESIGN.md)
- Add ESPN, Yahoo, FantasyPros scrapers
- Add more comprehensive error handling
- Improve test coverage to >80%

## Important Notes

1. **Separation of Concerns**: This server ONLY provides data. All analysis, recommendations, and strategy logic belongs in the MCP client (see `example-prompt.md`).

2. **Data Sources**: Currently using:
   - FantasySharks for player rankings (web scraping)
   - Google Sheets for draft tracking (API)

3. **No Persistence**: Rankings cache is in-memory only and resets when server restarts.

4. **Client Agnostic**: Works with any MCP client, not just Claude Code.
