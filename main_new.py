# Example usage in your main.py or registration handler
from queue_telegram_integration import QueueTelegramIntegration
import os

# Initialize the integration (do this once at app startup)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Store token in environment variable
telegram_integration = QueueTelegramIntegration(TELEGRAM_BOT_TOKEN)


# Example 1: Register ticket for immediate service (sync)
def register_immediate_service(chat_id, queue_name):
    """Register a ticket for immediate service."""
    ticket_number = generate_ticket_number()  # Your function
    
    result = telegram_integration.register_ticket_sync(
        chat_id=chat_id,
        ticket_number=ticket_number,
        queue_name=queue_name,
        estimated_wait_time="15-20 minutes",
        service_counter="Counter 3"
    )
    
    print(result)
    return ticket_number


# Example 2: Register appointment for future date (sync)
def register_appointment_service(chat_id, queue_name, appointment_date, appointment_time):
    """Register an appointment for a future date."""
    ticket_number = generate_ticket_number()  # Your function
    
    result = telegram_integration.register_ticket_sync(
        chat_id=chat_id,
        ticket_number=ticket_number,
        queue_name=queue_name,
        appointment_date=appointment_date,  # Format: YYYY-MM-DD
        appointment_time=appointment_time,  # Format: HH:MM
        service_counter="Counter 1",
        instructions="Please bring your ID and documents"
    )
    
    print(result)
    return ticket_number


# Example 3: Async version (if using async framework like FastAPI)
async def register_appointment_async(chat_id, queue_name, appointment_date):
    """Register appointment using async."""
    ticket_number = generate_ticket_number()
    
    result = await telegram_integration.register_ticket_async(
        chat_id=chat_id,
        ticket_number=ticket_number,
        queue_name=queue_name,
        appointment_date=appointment_date,
        estimated_wait_time="10 minutes"
    )
    
    return result


# Example 4: Cancel appointment reminder
def cancel_appointment(ticket_number, chat_id):
    """Cancel an appointment and its reminder."""
    success = telegram_integration.cancel_appointment_reminder(ticket_number, chat_id)
    if success:
        print(f"✅ Appointment reminder cancelled for ticket {ticket_number}")
    else:
        print(f"❌ Failed to cancel reminder")


# Example 5: View all scheduled reminders
def view_scheduled_reminders():
    """View all scheduled reminders."""
    reminders = telegram_integration.get_all_scheduled_reminders()
    for reminder in reminders:
        print(f"Job: {reminder['name']}, Next run: {reminder['next_run']}")


# At app shutdown
def shutdown_app():
    """Shutdown the app gracefully."""
    telegram_integration.shutdown()
