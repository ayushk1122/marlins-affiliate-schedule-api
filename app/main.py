from fastapi import FastAPI
from app.routes import schedule

app = FastAPI(
    title="Marlins Affiliate Schedule API",
    description="An internal API to fetch daily schedules and results for the Marlins and their minor league affiliates.",
    version="1.0.0"
)

# Register route(s)
app.include_router(schedule.router) 