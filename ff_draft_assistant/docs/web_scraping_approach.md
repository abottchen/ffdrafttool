# Web Scraping Approach

This document explains how the Fantasy Football Draft Assistant gathers data from publicly accessible websites without requiring API keys.

## Overview

The application uses web scraping to collect fantasy football data from public websites. This approach:
- Requires no API keys or authentication
- Uses only publicly accessible data
- Respects rate limits and robots.txt
- Implements polite scraping practices

## Data Sources

### 1. ESPN Fantasy Football
- **URL**: https://www.espn.com/fantasy/football/ffl/rankings
- **Data**: Player rankings, projections, news
- **Method**: HTML parsing of rankings tables

### 2. Yahoo Fantasy Sports  
- **URL**: https://football.fantasysports.yahoo.com/f1/draftanalysis
- **Data**: Rankings, ADP (Average Draft Position), analysis
- **Method**: HTML parsing, potentially AJAX endpoint discovery

### 3. FantasyPros
- **URL**: https://www.fantasypros.com/nfl/rankings/consensus-cheatsheets.php
- **Data**: Consensus rankings from multiple experts
- **Method**: Table parsing, aggregate data extraction

### 4. NFL.com Injuries
- **URL**: https://www.espn.com/nfl/injuries
- **Data**: Official injury designations
- **Method**: Parse injury report tables

## Implementation Details

### Web Scraper Architecture

```python
WebScraper (Abstract Base)
├── ESPNScraper
├── YahooScraper  
├── FantasyProsScraper
└── InjuryReportScraper
```

### Key Features

1. **Retry Logic**: Automatic retries with exponential backoff
2. **User Agent**: Proper browser user agent to avoid blocks
3. **Caching**: Temporary caching to reduce repeated requests
4. **Error Handling**: Graceful degradation if a source is unavailable

### Scraping Process

1. **Fetch Page**: Use aiohttp to asynchronously fetch HTML
2. **Parse HTML**: BeautifulSoup extracts structured data
3. **Normalize Data**: Convert to common Player model format
4. **Aggregate**: Combine rankings from multiple sources

## Ethical Considerations

- **Respect robots.txt**: Check and follow site policies
- **Rate Limiting**: Implement delays between requests
- **Caching**: Cache responses to minimize requests
- **User Agent**: Identify properly, don't masquerade as GoogleBot

## Handling Dynamic Content

Some sites load data via JavaScript. Strategies:

1. **Find API Endpoints**: Inspect network requests for JSON APIs
2. **Parse Initial State**: Extract data from script tags
3. **Browser Automation**: Use Playwright as last resort

## Data Quality

- **Name Matching**: Fuzzy matching for player names across sites
- **Team Normalization**: Standardize team abbreviations
- **Missing Data**: Handle gracefully when data is unavailable
- **Validation**: Ensure data makes sense (e.g., bye weeks 1-14)

## Example Implementation

See `src/services/web_scraper_example.py` for detailed examples of:
- Parsing HTML tables
- Extracting player data
- Handling different site structures
- Error handling patterns

## Testing

The scrapers include mock data for testing without hitting real websites:
- Unit tests verify scraper logic
- Integration tests use mock HTML responses
- Real scraping only happens in production

## Future Enhancements

1. **Smart Caching**: Cache based on update frequency
2. **Parallel Fetching**: Fetch multiple sources simultaneously  
3. **Change Detection**: Monitor for site structure changes
4. **Fallback Sources**: Alternative sites if primary fails