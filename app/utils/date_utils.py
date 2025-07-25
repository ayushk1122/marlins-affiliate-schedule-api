from datetime import datetime, date

def parse_date(date_str: str) -> date:
    """
    Parses a date string in YYYY-MM-DD format into a datetime.date object.
    If date_str is None, return today's date.
    """
    if date_str is None:
        return date.today()

    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return parsed_date
    except ValueError:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD.") 