from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.utils.date_utils import parse_date
from app.services.mlb_api import get_affiliates, get_schedule_for_teams

router = APIRouter()

@router.get("/schedule")
async def get_schedule(date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format")):
    try:
        parsed_date = parse_date(date)
        date_str = parsed_date.isoformat()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Step 1: Get affiliates
    affiliates = await get_affiliates()

    if not affiliates:
        return {"message": "No affiliates found."}

    # Step 2: Extract team and sport IDs
    team_ids = [team["id"] for team in affiliates]
    sport_ids = list(set(team["sport"]["id"] for team in affiliates))

    # Step 3: Fetch schedule
    schedule_data = await get_schedule_for_teams(team_ids, sport_ids, date_str)

    # TEMPORARY: Just return the raw response for now
    return {
        "date": date_str,
        "affiliate_count": len(affiliates),
        "games_found": len(schedule_data),
        "raw_schedule_data": schedule_data
    } 