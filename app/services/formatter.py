from typing import List, Dict, Any
from app.services.mlb_api import get_live_game_data, get_game_boxscore

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
                "probable_pitchers": {}  # Will be populated below
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

async def format_schedule_with_details(affiliates: List[Dict[str, Any]], schedule_data: List[Dict[str, Any]]) -> Dict[int, dict]:
    """
    Enhanced formatter that fetches detailed game data.
    """
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

    # Step 4: Process games with detailed data
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
        game_pk = game["gamePk"]

        # Basic metadata
        team_name = team_info[marlins_id]["team_name"]
        level = team_info[marlins_id]["level"]
        opponent_name = opponent_team["name"]
        parent_club = opponent_team["name"].split()[-1] if " " in opponent_name else opponent_name
        venue = game["venue"]["name"]
        
        # Map game state
        if status == "Preview":
            game_state = "Not Started"
        elif status == "Live":
            game_state = "In Progress"
        elif status == "Final":
            game_state = "Completed"
        else:
            game_state = status

        # Fetch detailed data based on game state
        if game_state == "Not Started":
            # Get probable pitchers from boxscore
            boxscore = await get_game_boxscore(game_pk)
            probable_pitchers = {}
            if boxscore:
                # Try multiple possible locations for probable pitchers
                home_team_data = boxscore.get("teams", {}).get("home", {})
                away_team_data = boxscore.get("teams", {}).get("away", {})
                
                # Method 1: Check probablePitcher field
                home_pitcher = home_team_data.get("probablePitcher", {})
                away_pitcher = away_team_data.get("probablePitcher", {})
                
                # Method 2: Check if no probable pitcher, try to get from players list
                if not home_pitcher and home_team_data.get("players"):
                    # Look for pitchers in the players list
                    for player_id, player_data in home_team_data.get("players", {}).items():
                        if player_data.get("position", {}).get("abbreviation") == "P":
                            home_pitcher = player_data.get("person", {})
                            break
                
                if not away_pitcher and away_team_data.get("players"):
                    for player_id, player_data in away_team_data.get("players", {}).items():
                        if player_data.get("position", {}).get("abbreviation") == "P":
                            away_pitcher = player_data.get("person", {})
                            break
                
                # Add pitchers if found
                if home_pitcher:
                    probable_pitchers["home"] = home_pitcher.get("fullName", "TBD")
                if away_pitcher:
                    probable_pitchers["away"] = away_pitcher.get("fullName", "TBD")
            
            # If still no probable pitchers, try the schedule endpoint data
            if not probable_pitchers:
                # Check if the game object has probable pitcher info
                home_probable = game.get("teams", {}).get("home", {}).get("probablePitcher", {})
                away_probable = game.get("teams", {}).get("away", {}).get("probablePitcher", {})
                
                if home_probable:
                    probable_pitchers["home"] = home_probable.get("fullName", "TBD")
                if away_probable:
                    probable_pitchers["away"] = away_probable.get("fullName", "TBD")
            
            details = {
                "game_time": game["gameDate"],
                "venue": venue,
                "probable_pitchers": probable_pitchers
            }

        elif game_state == "In Progress":
            # Get live game data
            live_data = await get_live_game_data(game_pk)
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
            
            if live_data:
                live_feed = live_data.get("liveData", {})
                plays = live_feed.get("plays", {})
                current_play = plays.get("currentPlay", {})
                all_plays = plays.get("allPlays", [])
                
                if current_play:
                    details["inning"] = current_play.get("about", {}).get("inning", "N/A")
                    details["outs"] = str(current_play.get("count", {}).get("outs", "N/A"))
                    
                    # Get current pitcher and batter
                    matchup = current_play.get("matchup", {})
                    if matchup:
                        details["current_pitcher"] = matchup.get("pitcher", {}).get("fullName", "N/A")
                        details["batter"] = matchup.get("batter", {}).get("fullName", "N/A")
                
                # Get runners on base from last play
                if all_plays:
                    last_play = all_plays[-1]
                    runners = last_play.get("runners", [])
                    runners_on_base = []
                    for runner in runners:
                        if runner.get("movement", {}).get("start") in ["1B", "2B", "3B"]:
                            runners_on_base.append(runner.get("movement", {}).get("start"))
                    details["runners_on_base"] = runners_on_base

        elif game_state == "Completed":
            # Get final stats from boxscore
            boxscore = await get_game_boxscore(game_pk)
            details = {
                "final_score": {
                    "home": game["teams"]["home"].get("score", 0),
                    "away": game["teams"]["away"].get("score", 0)
                },
                "winning_pitcher": "N/A",
                "losing_pitcher": "N/A",
                "save_pitcher": "N/A"
            }
            
            if boxscore:
                # Extract pitcher stats
                home_pitchers = boxscore.get("teams", {}).get("home", {}).get("pitchers", [])
                away_pitchers = boxscore.get("teams", {}).get("away", {}).get("pitchers", [])
                
                # Find winning and losing pitchers
                for pitcher_id in home_pitchers + away_pitchers:
                    pitcher_data = boxscore.get("teams", {}).get("home", {}).get("players", {}).get(f"ID{pitcher_id}", {})
                    if not pitcher_data:
                        pitcher_data = boxscore.get("teams", {}).get("away", {}).get("players", {}).get(f"ID{pitcher_id}", {})
                    
                    if pitcher_data:
                        stats = pitcher_data.get("stats", {}).get("pitching", {})
                        if stats.get("wins", 0) > 0:
                            details["winning_pitcher"] = pitcher_data.get("person", {}).get("fullName", "N/A")
                        elif stats.get("losses", 0) > 0:
                            details["losing_pitcher"] = pitcher_data.get("person", {}).get("fullName", "N/A")
                        elif stats.get("saves", 0) > 0:
                            details["save_pitcher"] = pitcher_data.get("person", {}).get("fullName", "N/A")
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