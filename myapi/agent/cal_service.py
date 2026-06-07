import requests
from backend.config import settings


class CalService:
    def __init__(self):
        self.api_key = settings.cal_api_key.get_secret_value()
        self.base_url = "https://api.cal.com/v2"
        self.event_type_id = 5650486

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "cal-api-version": "2024-08-13",
            "Content-Type": "application/json"
        }

    def get_slots(self, date_str):
        url = f"{self.base_url}/slots/available"
        params = {
            "eventTypeId": self.event_type_id,
            "startTime": f"{date_str}T00:00:00Z",
            "endTime": f"{date_str}T23:59:59Z"
        }

        response = requests.get(
            url,
            headers=self.headers,
            params=params
        )

        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("slots", {}).get(date_str, [])
    

    def create_booking(self, booking_data, user_details):
        patient_phone = user_details.get("phone", "000000")
        synthetic_email = f"hellodemo@clinic-internal.com"
        url = f"{self.base_url}/bookings"
        payload = {
            "start": booking_data["utc_time"],
            "eventTypeId": self.event_type_id,
            "attendee": {
                "name": user_details.get("name", "Patient"),
                "email": user_details.get(
                    "email",
                    synthetic_email
                ),
                "timeZone": "Asia/Kolkata",
                "language": "en"
            }
        }
        response = requests.post(
            url,
            headers=self.headers,
            json=payload
        )
        
        print(response.status_code)
        print(response.text)


        response.raise_for_status()

        
        return response.json()
    
    def cancel_booking(self, booking_uid):
        url= f"{self.base_url}/bookings/{booking_uid}/cancel"

        payload= {
            "cancellationReason": "Patient requested cancellation"
        }

        response= requests.post(
            url, 
            headers= self.headers,
            json= payload
        )
        
        response.raise_for_status()

        return response.json()
    
    def reschedule_booking(self, booking_uid, new_utc_time):
        url = f"{self.base_url}/bookings/{booking_uid}/reschedule"

        payload = {
            "start": new_utc_time,
            "reschedulingReason":
                "Patient requested reschedule"
        }

        response= requests.post(url,
                                headers= self.headers,
                                json= payload)
        print(response.status_code)
        print(response.text)

        response.raise_for_status()

        return response.json()
