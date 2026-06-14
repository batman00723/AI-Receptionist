import sib_api_v3_sdk
from backend.config import settings

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = settings.brevo_api_key.get_secret_value()

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration)
)


def send_emergency_alert(patient_phone: str, patient_issue: str):
    try:
        html = f"""
        <h3>Dental Emergency Notification</h3>
        <p><strong>Patient Contact Number:</strong> {patient_phone}</p>
        <p><strong>Message/Issue:</strong> {patient_issue}</p>
        <hr>
        <p>Sent via Caps & Crowns AI Assistant</p>
        """

        email = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": "AI Receptionist Bot",
                "email": "batmanmishra23@gmail.com"
            },
            to=[{"email": "amanmishrarewa23@gmail.com"}],
            subject="Patient Emergency Alert Email",
            html_content=html
        )

        response = api_instance.send_transac_email(email)

        print(f"Email sent successfully: {response}")
        return response

    except Exception as e:
        print(f"Error sending email: {e}")
        return None


def send_cancellation_alert(patient_phone: str, patient_issue: str):
    try:
        html = f"""
        <h3>Dental Cancellation Notification</h3>
        <p><strong>Patient Contact Number:</strong> {patient_phone}</p>
        <p><strong>Message/Issue:</strong> {patient_issue}</p>
        <hr>
        <p>Sent via Caps & Crowns AI Assistant</p>
        """

        email = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": "AI Receptionist Bot",
                "email": "batmanmishra23@gmail.com"
            },
            to=[{"email": "amanmishrarewa23@gmail.com"}],
            subject="Cancellation Alert Email",
            html_content=html
        )

        response = api_instance.send_transac_email(email)

        print(f"Email sent successfully: {response}")
        return response

    except Exception as e:
        print(f"Error sending email: {e}")
        return None