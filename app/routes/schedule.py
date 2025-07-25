from fastapi import APIRouter, Query
from typing import Optional
from app.utils.date_utils import parse_date
from app.services.mlb_api import get_affiliates

router = APIRouter()

@router.get("/schedule")
async def get_schedule(date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format")):
    parsed = parse_date(date)
    print(f"Parsed date: {parsed}")
    
    affiliates = await get_affiliates()
    print(f"Found {len(affiliates)} affiliates")
    
    # Temporary dummy data
    return {
        "146": {
            "team_name": "Miami Marlins",
            "level": "MLB",
            "opponent_name": "New York Mets",
            "opponent_mlb_parent": "Mets",
            "game_state": "Not Started",
            "details": {
                "game_time": "7:10 PM ET",
                "venue": "loanDepot Park",
                "probable_pitchers": {
                    "home": "Jesus Luzardo",
                    "away": "Kodai Senga"
                }
            }
        },
        "555": {}  # No game for this affiliate
    } 