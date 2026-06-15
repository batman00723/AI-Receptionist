from datetime import datetime
import pytz

def utc_to_ist(utc_time: str):
    dt = datetime.fromisoformat(
        utc_time.replace("Z", "+00:00")
    )

    ist = dt.astimezone(
        pytz.timezone("Asia/Kolkata")
    )

    return ist.strftime("%I:%M %p")