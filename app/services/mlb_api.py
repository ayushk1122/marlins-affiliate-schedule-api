import httpx
from app.config import BASE_URL, MARLINS_TEAM_ID
from typing import List, Dict, Any

async def get_affiliates() -> List[Dict[str, Any]]:
    """
    Fetch all Marlins affiliate teams for the 2025 season.
    """
    url = f"{BASE_URL}/teams/affiliates?teamIds={MARLINS_TEAM_ID}&year=2025"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    return data.get("teams", [])

async def get_schedule_for_teams(team_ids: List[int], sport_ids: List[int], date_str: str) -> List[Dict[str, Any]]:
    """
    Fetch schedule for given team and sport IDs on a specific date.
    """
    team_id_str = ",".join(str(id) for id in team_ids)
    sport_id_str = ",".join(str(id) for id in sport_ids)
    url = f"{BASE_URL}/schedule?teamId={team_id_str}&sportId={sport_id_str}&date={date_str}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json().get("dates", []) 