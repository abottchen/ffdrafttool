# Auction Rounds Strategy (Rounds 1-3)

## Overview
For the first 3 rounds of the DAN League draft, teams participate in an auction-style format. The draft assistant's role during these rounds is to **identify optimal players to target**, not to manage bidding or budget tracking.

## Draft Assistant's Role

### ✅ What the Assistant Should Do:
- **Analyze available players** using rankings and projections
- **Suggest optimal targets** based on team needs and strategy
- **Evaluate player value** relative to rankings and projections  
- **Consider positional scarcity** and roster construction
- **Assess injury risk** and player reliability
- **Provide player comparisons** for decision making

### ❌ What the Assistant Should NOT Do:
- Track auction budgets or spending
- Suggest bid amounts or bidding strategy
- Monitor other teams' auction behavior
- Provide auction-specific mechanics advice

## Key Considerations for Auction Rounds

### 1. **Player Analysis Focus**
- Use `get_player_rankings` to get comprehensive player evaluations
- Compare players across multiple ranking sources
- Focus on consensus rankings and expert analysis

### 2. **Team Strategy Alignment**  
- Consider what positions are most important to secure early
- Evaluate whether to target elite players or build depth
- Think about roster balance and long-term construction

### 3. **Risk Assessment**
- Evaluate injury history and current health status
- Consider age and potential decline
- Assess consistency vs. upside potential

### 4. **Positional Considerations**
- Identify positions with limited depth in later rounds
- Consider positions where top-tier talent provides significant advantage
- Plan for positional needs in snake draft rounds (5+)

## Tool Usage During Auction Rounds

### Primary Tools:
- `get_player_rankings` - Get player evaluations and projections
- `analyze_available_players` - Identify best available options
- `suggest_draft_pick` - Get targeted recommendations

### Strategy:
Use these tools to create a prioritized list of auction targets, then handle the actual bidding manually based on auction dynamics and budget considerations.

## Integration with Later Rounds

Remember that auction picks will affect:
- **Round 4 (Keeper)**: What positions still need to be filled
- **Rounds 5+ (Snake)**: Remaining roster needs and strategy
- **Overall team balance**: Ensuring auction picks complement snake draft strategy