@app.post("/api/counters/{counter_id}/call-next")
async def call_next_ticket(
    counter_id: int,
    db: Session = Depends(get_db)
):
    """Call next ticket in queue for this counter"""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()

    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )

    if not counter.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Counter is not active"
        )

    # Get service types for this counter
    service_types = counter.service_types.split(",")

    # Find next waiting ticket
    next_ticket = db.query(Ticket).filter(
        Ticket.service_type.in_([ServiceType(st) for st in service_types]),
        Ticket.status == TicketStatus.WAITING,
        Ticket.expires_at > datetime.utcnow()
    ).order_by(Ticket.created_at).first()

    if not next_ticket:
        return {
            "message": "No tickets waiting",
            "counter_number": counter.counter_number
        }

    # Update ticket status
    next_ticket.status = TicketStatus.CALLED
    next_ticket.counter_number = counter.counter_number
    next_ticket.called_at = datetime.utcnow()

    # Update counter
    counter.current_ticket_id = next_ticket.id

    db.commit()

    # Log action
    audit = AuditLog(
        action="TICKET_CALLED",
        ticket_id=next_ticket.id,
        counter_id=counter.id,
        details=f"Ticket {next_ticket.ticket_number} called to counter {counter.counter_number}"
    )
    db.add(audit)
    db.commit()

    # ========== SEND TELEGRAM NOTIFICATION ==========
    if (telegram_integration and 
        next_ticket.telegram_chat_id and 
        next_ticket.telegram_notification_sent):
        try:
            await telegram_integration.telegram_service.send_custom_message(
                chat_id=next_ticket.telegram_chat_id,
                message=f"""
<b>🔔 Your Turn!</b>

Your ticket <code>{next_ticket.ticket_number}</code> is being called.

<b>📍 Counter:</b> {counter.counter_number}
<b>🏢 Service:</b> {next_ticket.service_type.value}

Please proceed to the counter immediately!
"""
            )
        except Exception as e:
            logger.error(f"❌ Error sending Telegram notification: {str(e)}")

    return {
        "message": "Ticket called",
        "ticket_number": next_ticket.ticket_number,
        "counter_number": counter.counter_number,
        "full_name": next_ticket.full_name
    }
