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
   cd C:\Users\adam\Documents\Projects\ffdrafttool2\ff_draft_assistant
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

## 👤 Owner Configuration

The assistant can be personalized to recognize first-person references ("I", "me", "my team") as referring to your team.

## 🧪 Testing

Run the test suite:
```bash
pytest
```

## 💡 Usage Examples

### Basic Draft Assistance
```
Who should I pick next?
Show me the best available quarterbacks
What positions do I still need to fill?
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
ff_draft_assistant/
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
