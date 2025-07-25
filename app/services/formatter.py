from typing import List, Dict, Any, Union
from app.services.mlb_api import get_live_game_data, get_game_boxscore, get_live_feed_data, get_game_plays

def analyze_recent_plays_for_runners(plays_data: Dict[str, Any], current_inning: int, current_outs: int) -> List[str]:
    """
    Analyze recent plays to determine who's currently on base.
    """
    runners_on_base = []
    
    if not plays_data or "plays" not in plays_data:
        return runners_on_base
    
    plays = plays_data.get("plays", [])
    if not plays:
        return runners_on_base
    
    # Track base runners through recent plays
    current_runners = {"1B": None, "2B": None, "3B": None}
    
    # Look at plays from the current inning
    for play in reversed(plays):  # Start from most recent
        play_data = play.get("playEvents", [])
        inning = play.get("about", {}).get("inning", 0)
        
        # Only look at current inning plays
        if inning != current_inning:
            continue
            
        for event in play_data:
            event_type = event.get("details", {}).get("type", {})
            event_code = event_type.get("code", "")
            
            # Track base running events
            if "runner" in event:
                runner_data = event["runner"]
                runner_name = runner_data.get("details", {}).get("runner", {}).get("fullName", "")
                movement = runner_data.get("movement", {})
                start_base = movement.get("start", "")
                end_base = movement.get("end", "")
                
                # Update current runners based on movement
                if start_base == "1B" and end_base != "1B":
                    current_runners["1B"] = None
                if start_base == "2B" and end_base != "2B":
                    current_runners["2B"] = None
                if start_base == "3B" and end_base != "3B":
                    current_runners["3B"] = None
                    
                if end_base == "1B":
                    current_runners["1B"] = runner_name
                elif end_base == "2B":
                    current_runners["2B"] = runner_name
                elif end_base == "3B":
                    current_runners["3B"] = runner_name
    
    # Convert current runners to base positions
    for base, runner in current_runners.items():
        if runner:
            runners_on_base.append(base)
    
    return sorted(runners_on_base)

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
                "outs": "0",
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
            
            # First, try to get basic info from the game object itself
            game_status = game.get("status", {})
            details["inning"] = game_status.get("detailedState", "N/A")
            
            print(f"Fetching live data for game {game_pk}...")
            
            # Try to get live feed data first (for current game state)
            live_feed_data = await get_live_feed_data(game_pk)
            print(f"Live feed data result for game {game_pk}: {bool(live_feed_data)}")
            
            # Also get boxscore data (for historical info and current players)
            boxscore_data = await get_game_boxscore(game_pk)
            print(f"Boxscore data result for game {game_pk}: {bool(boxscore_data)}")
            
            # Get plays data for base runner analysis
            plays_data = await get_game_plays(game_pk)
            print(f"Plays data result for game {game_pk}: {bool(plays_data)}")

            # Process live feed data for current game state
            if live_feed_data:
                print(f"Live feed data keys: {list(live_feed_data.keys())}")
                
                # Extract current game state from live feed
                live_data = live_feed_data.get("liveData", {})
                if live_data:
                    # Get current inning, outs, and offense from linescore
                    linescore = live_data.get("linescore", {})
                    if linescore:
                        current_inning = linescore.get("currentInning", "N/A")
                        inning_half = linescore.get("inningHalf", "N/A")
                        outs = linescore.get("outs", "N/A")
                        
                        if current_inning and inning_half:
                            details["inning"] = f"{inning_half} {current_inning}"
                            print(f"    Live feed inning: {details['inning']}")
                        
                        if outs != "N/A":
                            details["outs"] = str(outs)
                            print(f"    Live feed outs: {details['outs']}")
                    
                    # Get current batter and runners from offense
                    offense = linescore.get("offense", {})
                    if offense:
                        # Get current batter
                        batter_info = offense.get("batter", {})
                        if isinstance(batter_info, dict) and batter_info.get("fullName"):
                            details["batter"] = batter_info["fullName"]
                            print(f"    Live feed batter: {details['batter']}")
                        
                        # Get runners on base
                        runners_on_base = []
                        on_first = offense.get("first")
                        on_second = offense.get("second") 
                        on_third = offense.get("third")
                        
                        if on_first and isinstance(on_first, dict) and on_first.get("fullName"):
                            runners_on_base.append(f"1B: {on_first.get('fullName')}")
                            print(f"    Found runner on 1B: {on_first.get('fullName')}")
                        if on_second and isinstance(on_second, dict) and on_second.get("fullName"):
                            runners_on_base.append(f"2B: {on_second.get('fullName')}")
                            print(f"    Found runner on 2B: {on_second.get('fullName')}")
                        if on_third and isinstance(on_third, dict) and on_third.get("fullName"):
                            runners_on_base.append(f"3B: {on_third.get('fullName')}")
                            print(f"    Found runner on 3B: {on_third.get('fullName')}")
                        
                        details["runners_on_base"] = sorted(runners_on_base)
                        print(f"    Live feed runners: {details['runners_on_base']}")
                    
                    # Get current pitcher from defense
                    defense = linescore.get("defense", {})
                    if defense:
                        pitcher_info = defense.get("pitcher", {})
                        if isinstance(pitcher_info, dict) and pitcher_info.get("fullName"):
                            details["current_pitcher"] = pitcher_info["fullName"]
                            print(f"    Live feed pitcher: {details['current_pitcher']}")
            
            # Process boxscore data as fallback (only for pitcher/batter if live feed didn't provide them)
            if boxscore_data and (details["current_pitcher"] == "N/A" or details["batter"] == "N/A"):
                print(f"Boxscore data keys: {list(boxscore_data.keys())}")

                # Check if this is boxscore data (which has different structure)
                if "teams" in boxscore_data and "info" in boxscore_data:
                    print("Processing boxscore data for live game...")
                    
                    # Get current pitcher and batter from teams data
                    teams = boxscore_data.get("teams", {})
                    
                    # Look for current pitcher and batter using gameStatus
                    for team_side in ["home", "away"]:
                        team_data = teams.get(team_side, {})
                        players = team_data.get("players", {})
                        
                        for player_id, player_data in players.items():
                            game_status = player_data.get("gameStatus", {})
                            
                            # Check if this is the current pitcher
                            if game_status.get("isCurrentPitcher", False):
                                details["current_pitcher"] = player_data.get("person", {}).get("fullName", "N/A")
                                print(f"    Found current pitcher: {details['current_pitcher']}")
                                
                                # Extract inning and outs from current pitcher's stats
                                pitcher_stats = player_data.get("stats", {}).get("pitching", {})
                                if pitcher_stats:
                                    # Get innings pitched (e.g., "2.2" means 2 innings + 2 outs = 8 outs total)
                                    innings_pitched = pitcher_stats.get("inningsPitched", "0.0")
                                    
                                    # Check if this pitcher has pitched any innings
                                    if innings_pitched and innings_pitched != "0.0":
                                        try:
                                            # Parse innings like "2.2" (2 innings, 2 outs)
                                            if "." in innings_pitched:
                                                full_innings, partial_outs = innings_pitched.split(".")
                                                total_outs = int(full_innings) * 3 + int(partial_outs)
                                                details["outs"] = str(total_outs % 3)  # Current outs in this inning
                                                
                                                # Calculate current inning
                                                total_innings = int(full_innings) + (int(partial_outs) // 3)
                                                # Determine if home or away team is batting based on current batter
                                                inning_half = "Bottom"  # Default assumption
                                                details["inning"] = f"{inning_half} {total_innings + 1}"
                                            else:
                                                total_innings = int(innings_pitched)
                                                details["outs"] = "0"  # Start of new inning
                                                inning_half = "Bottom"  # Default assumption
                                                details["inning"] = f"{inning_half} {total_innings + 1}"
                                            
                                            print(f"    Extracted from pitcher stats: Inning {details['inning']}, Outs {details['outs']}")
                                            
                                        except (ValueError, TypeError) as e:
                                            print(f"    Error parsing pitcher stats: {e}")
                                    else:
                                        # New pitcher with no innings pitched - need to get inning from other sources
                                        print(f"    New pitcher detected (0.0 IP) - getting inning from game status")
                                        
                                        # Try to get inning from game status detailed state
                                        game_status_detailed = game_status.get("detailedState", "")
                                        if game_status_detailed:
                                            # Look for inning info in detailed state like "Bottom 5th" or "Top 3rd"
                                            import re
                                            inning_match = re.search(r'(top|bottom)\s*(\d+)(?:st|nd|rd|th)?', game_status_detailed.lower())
                                            if inning_match:
                                                inning_half = inning_match.group(1).title()
                                                inning_num = inning_match.group(2)
                                                details["inning"] = f"{inning_half} {inning_num}"
                                                print(f"    Extracted from game status: {details['inning']}")
                                            
                                            # Try to get outs from detailed state
                                            outs_match = re.search(r'(\d+)\s*out', game_status_detailed.lower())
                                            if outs_match:
                                                details["outs"] = outs_match.group(1)
                                                print(f"    Extracted outs from game status: {details['outs']}")
                                        
                                        # If still no inning info, try to get from current pitcher's total outs
                                        if details["inning"] == "N/A":
                                            # Calculate inning from current pitcher's total outs
                                            total_outs_pitched = pitcher_stats.get("outs", 0)
                                            if total_outs_pitched > 0:
                                                # Calculate completed innings from total outs
                                                completed_innings = total_outs_pitched // 3
                                                current_inning = completed_innings + 1
                                                
                                                # Determine which team is batting based on current batter
                                                if team_side == "away":
                                                    # Away team batting = Top of inning
                                                    inning_half = "Top"
                                                else:
                                                    # Home team batting = Bottom of inning
                                                    inning_half = "Bottom"
                                                
                                                details["inning"] = f"{inning_half} {current_inning}"
                                                print(f"    Calculated inning from pitcher total outs: {details['inning']} (Pitcher outs: {total_outs_pitched})")
                                        
                                        # If still no inning info, try to get from team stats using total outs
                                        if details["inning"] == "N/A":
                                            # Look at team stats to determine current inning from total outs
                                            home_team_stats = boxscore_data.get("teams", {}).get("home", {}).get("teamStats", {})
                                            away_team_stats = boxscore_data.get("teams", {}).get("away", {}).get("teamStats", {})
                                            
                                            if home_team_stats and away_team_stats:
                                                # Get total outs for each team
                                                home_outs = home_team_stats.get("batting", {}).get("leftOnBase", 0)  # This might not be total outs
                                                away_outs = away_team_stats.get("batting", {}).get("leftOnBase", 0)
                                                
                                                # Try to get outs from pitching stats (outs recorded by opposing pitchers)
                                                home_pitching_outs = home_team_stats.get("pitching", {}).get("outs", 0)
                                                away_pitching_outs = away_team_stats.get("pitching", {}).get("outs", 0)
                                                
                                                # Calculate inning from total outs (27 outs per 9 innings)
                                                total_outs = home_pitching_outs + away_pitching_outs
                                                completed_innings = total_outs // 3  # 3 outs per inning
                                                
                                                # Determine which team is batting based on current batter
                                                if team_side == "away":
                                                    # Away team batting = Top of inning
                                                    inning_half = "Top"
                                                    current_inning = completed_innings + 1
                                                else:
                                                    # Home team batting = Bottom of inning
                                                    inning_half = "Bottom"
                                                    current_inning = completed_innings + 1
                                                
                                                details["inning"] = f"{inning_half} {current_inning}"
                                                print(f"    Calculated inning from total outs: {details['inning']} (Total outs: {total_outs})")
                                
                                # Try to determine runners on base from pitcher's recent performance
                                if pitcher_stats:
                                    hits = pitcher_stats.get("hits", 0)
                                    base_on_balls = pitcher_stats.get("baseOnBalls", 0)
                                    hit_by_pitch = pitcher_stats.get("hitBatsmen", 0)
                                    batters_faced = pitcher_stats.get("battersFaced", 0)
                                    
                                    if batters_faced > 0:
                                        print(f"    Pitcher stats: {hits} hits, {base_on_balls} walks, {hit_by_pitch} HBP, {batters_faced} batters faced")
                            
                            # Check if this is the current batter
                            if game_status.get("isCurrentBatter", False):
                                details["batter"] = player_data.get("person", {}).get("fullName", "N/A")
                                print(f"    Found current batter: {details['batter']}")
                                
                                # Determine which team is batting (top/bottom)
                                if team_side == "away":
                                    # Away team batting = Top of inning
                                    if "inning" in details and "Bottom" in details["inning"]:
                                        details["inning"] = details["inning"].replace("Bottom", "Top")
                                        print(f"    Corrected inning: {details['inning']} (away team batting)")
                                else:
                                    # Home team batting = Bottom of inning
                                    if "inning" in details and "Top" in details["inning"]:
                                        details["inning"] = details["inning"].replace("Top", "Bottom")
                                        print(f"    Corrected inning: {details['inning']} (home team batting)")
                    
                    # Extract runners on base from plays analysis (if not already set by live feed)
                    if not details["runners_on_base"] and plays_data:
                        # Extract current inning number from the inning string
                        current_inning_str = details["inning"]
                        current_inning = 1  # Default
                        try:
                            # Extract number from "Top 5" or "Bottom 3"
                            import re
                            inning_match = re.search(r'(\d+)', current_inning_str)
                            if inning_match:
                                current_inning = int(inning_match.group(1))
                        except (ValueError, TypeError):
                            current_inning = 1
                        
                        # Analyze recent plays for current base runners
                        runners_on_base = analyze_recent_plays_for_runners(plays_data, current_inning, int(details["outs"]))
                        details["runners_on_base"] = runners_on_base
                        print(f"    Analyzed plays for runners: {runners_on_base}")
                    
                    # Fallback to info array if plays analysis didn't work
                    if not details["runners_on_base"]:
                        runners_on_base = []
                        
                        # First, try to get runners from "Runners left in scoring position" info
                        for item in info:
                            label = item.get("label", "")
                            value = item.get("value", "")
                            
                            # Look for runners on base information
                            if "Runners left in scoring position" in label:
                                # Parse runners from value like "Lopez, O; Edwards, X."
                                if value and value != "None":
                                    # Extract base positions from the label
                                    if "2 out" in label:
                                        # Runners on 2nd and 3rd with 2 outs
                                        runners_on_base.extend(["2B", "3B"])
                                    elif "1 out" in label:
                                        # Runners on 2nd and 3rd with 1 out
                                        runners_on_base.extend(["2B", "3B"])
                                    else:
                                        # Default to 2nd and 3rd if no out count specified
                                        runners_on_base.extend(["2B", "3B"])
                            
                            # Look for other runner indicators
                            elif "LOB" in label and value and value != "0":
                                # Left on base indicates runners
                                if "1" in value:
                                    runners_on_base.append("1B")
                                if "2" in value:
                                    runners_on_base.append("2B")
                                if "3" in value:
                                    runners_on_base.append("3B")
                        
                        # If no runners found from info, try to determine from recent plays
                        if not runners_on_base:
                            # Look for recent base-running events in the info array
                            for item in info:
                                label = item.get("label", "")
                                value = item.get("value", "")
                                
                                # Look for stolen bases, doubles, triples, etc.
                                if "SB" in label and value:
                                    # Stolen base indicates runner on 2B or 3B
                                    if "2nd" in value or "2B" in value:
                                        runners_on_base.append("2B")
                                    elif "3rd" in value or "3B" in value:
                                        runners_on_base.append("3B")
                                
                                # Look for doubles and triples
                                elif "2B" in label and value and value != "None":
                                    # Double indicates runner on 2B
                                    runners_on_base.append("2B")
                                
                                elif "3B" in label and value and value != "None":
                                    # Triple indicates runner on 3B
                                    runners_on_base.append("3B")
                                
                                # Look for recent hits that might indicate runners
                                elif "TB" in label and value:
                                    # Total bases - look for recent hits
                                    if "2" in value:  # Double
                                        runners_on_base.append("2B")
                                    elif "3" in value:  # Triple
                                        runners_on_base.append("3B")
                                    elif "1" in value and "2" not in value and "3" not in value:  # Single
                                        runners_on_base.append("1B")
                        
                        # Remove duplicates and sort
                        runners_on_base = sorted(list(set(runners_on_base)))
                        details["runners_on_base"] = runners_on_base
                        
                        print(f"    Extracted runners from info: {runners_on_base}")
                    
                    # If we still don't have proper inning info, try to get it from the game status
                    if details["inning"] == "N/A" or details["inning"] == "In Progress":
                        # Use the detailed state from the original game object
                        details["inning"] = game_status.get("detailedState", "In Progress")
                    
                    # If we still don't have outs, try to get from game status
                    if details["outs"] == "N/A":
                        # Try to extract outs from the detailed state or other sources
                        detailed_state = game_status.get("detailedState", "")
                        if "out" in detailed_state.lower():
                            # Extract number from "2 outs" or similar
                            import re
                            outs_match = re.search(r'(\d+)\s*out', detailed_state.lower())
                            if outs_match:
                                details["outs"] = outs_match.group(1)
                    
                    # Try to get inning from the detailed state if not found in info
                    if details["inning"] == "N/A" or details["inning"] == "In Progress":
                        detailed_state = game_status.get("detailedState", "")
                        if "inning" in detailed_state.lower():
                            # Extract inning info from detailed state
                            import re
                            inning_match = re.search(r'(top|bottom)\s*(\d+)(?:st|nd|rd|th)?', detailed_state.lower())
                            if inning_match:
                                inning_part = inning_match.group(1).title()
                                inning_num = inning_match.group(2)
                                details["inning"] = f"{inning_part} {inning_num}"
                    
                    # Try to get outs from info array more thoroughly
                    if details["outs"] == "N/A":
                        for item in info:
                            label = item.get("label", "")
                            if "out" in label.lower():
                                # Extract number from labels like "2 out"
                                import re
                                outs_match = re.search(r'(\d+)\s*out', label.lower())
                                if outs_match:
                                    details["outs"] = outs_match.group(1)
                                    break
                    
                    print(f"  Boxscore processing results:")
                    print(f"    - Inning: {details['inning']}")
                    print(f"    - Outs: {details['outs']}")
                    print(f"    - Current Pitcher: {details['current_pitcher']}")
                    print(f"    - Current Batter: {details['batter']}")
                    print(f"    - Runners on base: {details['runners_on_base']}")
                
                else:
                    # Original live feed processing
                    live_feed = live_data.get("liveData", {})
                    print(f"Live feed keys: {list(live_feed.keys())}")
                    
                    plays = live_feed.get("plays", {})
                    current_play = plays.get("currentPlay", {})
                    all_plays = plays.get("allPlays", [])
                    
                    print(f"  - Has liveData: {bool(live_feed)}")
                    print(f"  - Has plays: {bool(plays)}")
                    print(f"  - Has currentPlay: {bool(current_play)}")
                    print(f"  - All plays count: {len(all_plays) if all_plays else 0}")
                    
                    # Get inning information from live data if available
                    if current_play:
                        about = current_play.get("about", {})
                        live_inning = f"{about.get('inningState', '')} {about.get('inning', '')}".strip()
                        if live_inning and live_inning != "N/A":
                            details["inning"] = live_inning
                        details["outs"] = str(current_play.get("count", {}).get("outs", "N/A"))
                        
                        # Get current pitcher and batter
                        matchup = current_play.get("matchup", {})
                        if matchup:
                            pitcher = matchup.get("pitcher", {})
                            batter = matchup.get("batter", {})
                            if pitcher:
                                details["current_pitcher"] = pitcher.get("fullName", "N/A")
                            if batter:
                                details["batter"] = batter.get("fullName", "N/A")
                    
                    # Get runners on base from current situation
                    if all_plays:
                        last_play = all_plays[-1]
                        runners = last_play.get("runners", [])
                        runners_on_base = []
                        for runner in runners:
                            movement = runner.get("movement", {})
                            start = movement.get("start")
                            end = movement.get("end")
                            # Check if runner is still on base
                            if start in ["1B", "2B", "3B"] and end not in ["1B", "2B", "3B", "HOME"]:
                                runners_on_base.append(start)
                            elif end in ["1B", "2B", "3B"]:
                                runners_on_base.append(end)
                        details["runners_on_base"] = runners_on_base
                    
                    # Alternative: Try to get data from live feed structure
                    if details["current_pitcher"] == "N/A":
                        live_plays = live_feed.get("plays", {})
                        if live_plays:
                            # Try to get from the most recent play
                            recent_plays = live_plays.get("allPlays", [])
                            if recent_plays:
                                latest_play = recent_plays[-1]
                                matchup = latest_play.get("matchup", {})
                                if matchup:
                                    pitcher = matchup.get("pitcher", {})
                                    if pitcher:
                                        details["current_pitcher"] = pitcher.get("fullName", "N/A")
            else:
                print(f"No live data available for game {game_pk}")
                # Use the game status as fallback
                if details["inning"] == "N/A":
                    details["inning"] = game_status.get("detailedState", "In Progress")

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