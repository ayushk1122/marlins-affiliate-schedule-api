# Marlins Affiliate Schedule API

A FastAPI-based web service that provides real-time schedules and live game data for the Miami Marlins (and any other MLB team) and their minor league affiliates. The API fetches data from MLB's official API and provides enhanced formatting with live game state information.

## 🏟️ Features

- **Real-time Schedule Data**: Get daily schedules for all Marlins/MLB team affiliates
- **Live Game State**: Current inning, outs, runners on base, pitcher, and batter for games in progress
- **Multi-level Support**: MLB, AAA, AA, A+, A, and Rookie League teams
- **Enhanced Data Formatting**: Clean, structured responses with detailed game information
- **Dual API Integration**: Uses MLB API v1 for historical data and v1.1 for live feed data

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd marlins-affiliate-schedule-api
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   
   **Windows:**
   ```bash
   .venv\Scripts\activate
   ```
   
   **macOS/Linux:**
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

   Or alternatively:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Schedule Endpoint: http://localhost:8000/schedule
   - Health Check: http://localhost:8000/

## 📋 API Endpoints

### GET `/schedule`
Retrieves the schedule for all Marlins/MLB team affiliates for a specific date.

**Query Parameters:**
- `date` (optional): Date in YYYY-MM-DD format (defaults to today)

**Example Request:**
```bash
curl "http://localhost:8000/schedule?date=2025-07-25"
```

**Example Response:**
```json
{
  "146": {
    "team_name": "Miami Marlins",
    "level": "MLB",
    "opponent_name": "Milwaukee Brewers",
    "opponent_mlb_parent": "Brewers",
    "game_state": "In Progress",
    "details": {
      "venue": "American Family Field",
      "score": {
        "home": 1,
        "away": 5
      },
      "inning": "Bottom 7",
      "outs": "2",
      "runners_on_base": [
        "1B: Tyler Black",
        "2B: Isaac Collins"
      ],
      "current_pitcher": "Anthony Bender",
      "batter": "Blake Perkins"
    }
  }
}
```

## 🏗️ Project Structure

```
marlins-affiliate-schedule-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration constants
│   ├── models/
│   │   ├── __init__.py
│   │   └── game_response.py    # Pydantic models for API responses
│   ├── routes/
│   │   ├── __init__.py
│   │   └── schedule.py         # API route handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── mlb_api.py          # MLB API integration
│   │   └── formatter.py        # Data formatting and processing
│   └── utils/
│       ├── __init__.py
│       └── date_utils.py       # Date parsing utilities
├── tests/                      # Test files
├── requirements.txt            # Python dependencies
├── run.py                      # Application runner
└── README.md                   # This file
```

## ⚙️ Configuration

### Team Configuration
The API is configurable to work with any MLB team by modifying `app/config.py`:

```python
# Change this to any MLB team ID to get their affiliates
MARLINS_TEAM_ID = 146  # Miami Marlins

### API Configuration
```python
BASE_URL = "https://statsapi.mlb.com/api/v1"           # For schedules, boxscores, etc.
LIVE_FEED_BASE_URL = "https://statsapi.mlb.com/api/v1.1"  # For live game data
MLB_SPORT_ID = 1  # Baseball sport ID
```

## 🔧 Key Components

### Core Technologies
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **httpx**: Async HTTP client for API requests
- **Pydantic**: Data validation and settings management

### MLB API Integration
The project integrates with MLB's official API using two different versions:

- **v1 API** (`https://statsapi.mlb.com/api/v1`): Used for historical data, schedules, boxscores, and completed games
- **v1.1 API** (`https://statsapi.mlb.com/api/v1.1`): Used specifically for live feed data with real-time game state

### Key Services

#### `mlb_api.py`
- Handles all MLB API communication
- Implements retry logic and error handling
- Manages different API endpoints for various data types

#### `formatter.py`
- Processes raw MLB API data into clean, structured responses
- Implements live game state detection and formatting
- Handles different game states (Scheduled, In Progress, Completed)

#### `schedule.py`
- Defines the main API endpoint
- Handles request validation and response formatting
- Manages date parsing and error handling

## 🎯 Game State Detection

The API provides different levels of detail based on game status:

### Scheduled Games
- Basic game information (teams, venue, time)
- Probable pitchers (when available)

### In Progress Games
- Real-time inning and outs
- Current pitcher and batter
- Runners on base with player names
- Live score updates

### Completed Games
- Final scores
- Winning/losing/save pitchers
- Game statistics
