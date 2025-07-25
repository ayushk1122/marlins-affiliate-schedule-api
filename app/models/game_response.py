from pydantic import BaseModel, Field, RootModel
from typing import Dict, Optional, List, Union

class NotStartedDetails(BaseModel):
    """Details for games that haven't started yet."""
    game_time: str = Field(..., description="Game start time in ISO format")
    venue: str = Field(..., description="Venue name")
    probable_pitchers: Dict[str, str] = Field(default_factory=dict, description="Probable pitchers if available")

class InProgressDetails(BaseModel):
    """Details for games currently in progress."""
    venue: str = Field(..., description="Venue name")
    score: Dict[str, int] = Field(..., description="Current score (home/away)")
    inning: str = Field(..., description="Current inning")
    outs: str = Field(..., description="Number of outs")
    runners_on_base: List[str] = Field(default_factory=list, description="Runners on base")
    current_pitcher: str = Field(..., description="Current pitcher")
    batter: str = Field(..., description="Current batter")

class CompletedDetails(BaseModel):
    """Details for completed games."""
    final_score: Dict[str, int] = Field(..., description="Final score (home/away)")
    winning_pitcher: str = Field(..., description="Winning pitcher")
    losing_pitcher: str = Field(..., description="Losing pitcher")
    save_pitcher: Optional[str] = Field(None, description="Save pitcher if applicable")

class TeamGame(BaseModel):
    """Structure for a team's game information."""
    team_name: str = Field(..., description="Team name")
    level: str = Field(..., description="League level (MLB, AAA, AA, A+, A, R)")
    opponent_name: str = Field(..., description="Opponent team name")
    opponent_mlb_parent: str = Field(..., description="Opponent's MLB parent club")
    game_state: str = Field(..., description="Game state: Not Started, In Progress, or Completed")
    details: Optional[Union[NotStartedDetails, InProgressDetails, CompletedDetails]] = Field(
        None, 
        description="Game details based on state"
    )

class ScheduleResponse(RootModel):
    """Main response model for the schedule endpoint."""
    root: Dict[int, Union[TeamGame, Dict]] = Field(
        ..., 
        description="Schedule data keyed by team ID. Empty dict {} means no game for that team."
    ) 