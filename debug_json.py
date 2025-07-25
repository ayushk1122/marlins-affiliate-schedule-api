#!/usr/bin/env python3
"""
Debug script to explore MLB API JSON structure and find inning, outs, and runners on base.
"""

import asyncio
import json
from app.services.mlb_api import get_live_game_data

async def debug_game_data(game_pk: int):
    """Debug a specific game to find inning, outs, and runners on base data."""
    print(f"🔍 Debugging game {game_pk}...")
    
    # Get the live data
    live_data = await get_live_game_data(game_pk)
    
    if not live_data:
        print("❌ No live data found")
        return
    
    print(f"✅ Found live data with keys: {list(live_data.keys())}")
    
    # Save full response to file for inspection
    with open(f"debug_game_{game_pk}.json", "w") as f:
        json.dump(live_data, f, indent=2)
    print(f"💾 Full response saved to debug_game_{game_pk}.json")
    
    # Explore the structure systematically
    print("\n" + "="*50)
    print("🔍 EXPLORING JSON STRUCTURE")
    print("="*50)
    
    # Check if it's boxscore data
    if "teams" in live_data and "info" in live_data:
        print("📊 This appears to be boxscore data")
        
        # Explore info array
        info = live_data.get("info", [])
        print(f"\n📋 INFO ARRAY ({len(info)} items):")
        for i, item in enumerate(info):
            label = item.get("label", "")
            value = item.get("value", "")
            print(f"  {i}: {label} = {value}")
            
            # Highlight potential inning/outs/runners data
            if any(keyword in label.lower() for keyword in ["inning", "out", "runner", "base", "lob"]):
                print(f"    ⭐ POTENTIAL: {label} = {value}")
        
        # Explore teams structure
        teams = live_data.get("teams", {})
        print(f"\n🏟️ TEAMS KEYS: {list(teams.keys())}")
        
        for team_side in ["home", "away"]:
            if team_side in teams:
                team_data = teams[team_side]
                print(f"\n  {team_side.upper()} TEAM KEYS: {list(team_data.keys())}")
                
                # Look for players
                players = team_data.get("players", {})
                print(f"    Players count: {len(players)}")
                
                # Find current pitcher and batter
                for player_id, player_data in players.items():
                    game_status = player_data.get("gameStatus", {})
                    if game_status.get("isCurrentPitcher") or game_status.get("isCurrentBatter"):
                        name = player_data.get("person", {}).get("fullName", "Unknown")
                        is_pitcher = game_status.get("isCurrentPitcher", False)
                        is_batter = game_status.get("isCurrentBatter", False)
                        print(f"    ⭐ CURRENT PLAYER: {name} (Pitcher: {is_pitcher}, Batter: {is_batter})")
    
    # Check for other potential data structures
    print(f"\n🔍 OTHER POTENTIAL DATA SOURCES:")
    
    # Look for any field containing inning/out/runner keywords
    def search_for_keywords(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    search_for_keywords(value, current_path)
                elif isinstance(value, str) and any(keyword in value.lower() for keyword in ["inning", "out", "runner", "base"]):
                    print(f"    ⭐ {current_path}: {value}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                search_for_keywords(item, current_path)
    
    search_for_keywords(live_data)
    
    print(f"\n💡 SUGGESTIONS:")
    print("1. Check the debug_game_{game_pk}.json file for the full structure")
    print("2. Look for 'info' array items with inning/out/runner keywords")
    print("3. Check if there's a separate 'liveData' or 'feed' structure")
    print("4. Look for game status information in the original game object")

async def main():
    """Main function to run the debug script."""
    # Use a game that's currently in progress
    # You can change this to any game_pk you want to debug
    game_pk = 777008  # This was the Marlins game from your example
    
    print("🚀 Starting JSON Structure Debug")
    print(f"🎯 Debugging game: {game_pk}")
    
    await debug_game_data(game_pk)
    
    print("\n✅ Debug complete! Check the generated JSON file for detailed structure.")

if __name__ == "__main__":
    asyncio.run(main()) 