from typing import List, Dict, Any

def format_schedule(affiliates: List[Dict[str, Any]], schedule_data: List[Dict[str, Any]]) -> Dict[int, dict]:
    # Level mapping
    LEVEL_MAP = {
        "Major League Baseball": "MLB",
        "Triple-A": "AAA",
        "Double-A": "AA",
        "High-A": "A+",
        "Single-A": "A",
        "Rookie": "R"
    }

    # Step 1: Create team lookup
    team_info = {}
    for team in affiliates:
        sport = team.get("sport", {})
        # Use the mapped abbreviation if available, else fallback to abbreviation or name
        raw_level = sport.get("name", sport.get("abbreviation", "Unknown"))
        level = LEVEL_MAP.get(raw_level, sport.get("abbreviation", raw_level))
        team_info[team["id"]] = {
            "team_name": team["name"],
            "level": level
        }

    # Step 2: Initialize base response
    response = {team_id: {} for team_id in team_info}

    # Step 3: Extract all games
    games = []
    for day in schedule_data:
        games.extend(day.get("games", []))

    # Step 4: Process games
    for game in games:
        status = game["status"]["abstractGameState"]
        home_team = game["teams"]["home"]["team"]
        away_team = game["teams"]["away"]["team"]

        # Determine if one of the teams is a Marlins affiliate
        marlins_team = None
        opponent_team = None
        is_home = False

        if home_team["id"] in team_info:
            marlins_team = home_team
            opponent_team = away_team
            is_home = True
        elif away_team["id"] in team_info:
            marlins_team = away_team
            opponent_team = home_team
            is_home = False
        else:
            continue  # skip non-affiliate games

        marlins_id = marlins_team["id"]

        # Basic metadata
        team_name = team_info[marlins_id]["team_name"]
        level = team_info[marlins_id]["level"]
        opponent_name = opponent_team["name"]

        # Opponent MLB parent if applicable (only if it's a minor league team)
        parent_club = opponent_team["name"].split()[-1] if " " in opponent_name else opponent_name

        # Common info
        venue = game["venue"]["name"]
        
        # Map game state to required format
        if status == "Preview":
            game_state = "Not Started"
        elif status == "Live":
            game_state = "In Progress"
        elif status == "Final":
            game_state = "Completed"
        else:
            game_state = status

        # Format by game state
        if game_state == "Not Started":
            details = {
                "game_time": game["gameDate"],
                "venue": venue,
                "probable_pitchers": {}  # MLB API may have them in liveData, left blank for now
            }

        elif game_state == "In Progress":
            details = {
                "venue": venue,
                "score": {
                    "home": game["teams"]["home"].get("score", 0),
                    "away": game["teams"]["away"].get("score", 0)
                },
                "inning": "N/A",
                "outs": "N/A",
                "runners_on_base": [],
                "current_pitcher": "N/A",
                "batter": "N/A"
            }

        elif game_state == "Completed":
            details = {
                "final_score": {
                    "home": game["teams"]["home"].get("score", 0),
                    "away": game["teams"]["away"].get("score", 0)
                },
                "winning_pitcher": "N/A",
                "losing_pitcher": "N/A",
                "save_pitcher": "N/A"
            }
        else:
            details = {}

        # Construct the output
        response[marlins_id] = {
            "team_name": team_name,
            "level": level,
            "opponent_name": opponent_name,
            "opponent_mlb_parent": parent_club,
            "game_state": game_state,
            "details": details
        }

    return response 