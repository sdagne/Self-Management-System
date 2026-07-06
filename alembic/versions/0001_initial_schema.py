"""Initial schema: citizens, tickets, counters, audit_logs

Revision ID: 0001
Revises:
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "citizens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("id_number_hash", sa.String(), unique=True, index=True, nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_blacklisted", sa.Boolean(), default=False),
        sa.Column("blacklist_reason", sa.String(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(), unique=True, index=True, nullable=True),
        sa.Column("telegram_notifications_enabled", sa.Boolean(), default=True),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("ticket_number", sa.String(), unique=True, index=True, nullable=False),
        sa.Column("citizen_id", sa.Integer(), nullable=False),
        sa.Column("id_number_hash", sa.String(), index=True, nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column(
            "service_type",
            sa.Enum(
                "kebele_id", "birth_certificate", "fayda_id", "national_id",
                "land_construction_permit", "land_maps", "land_registration",
                "passport_renewal", "visa_services", "yellow_card", "travel_documents",
                "business_license", "business_registration", "import_export",
                "driver_license_renewal", "driver_license_new", "vehicle_registration",
                "ethio_telecom", "sim_registration", "commercial_bank", "financial_services",
                "ethio_post", "mail_services", "document_legalization", "tax_service",
                "education_services", "health_services", "immigration", "other",
                name="servicetype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "waiting", "called", "serving", "completed", "expired", "cancelled",
                name="ticketstatus",
            ),
            default="waiting",
        ),
        sa.Column("counter_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("called_at", sa.DateTime(), nullable=True),
        sa.Column("served_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("qr_code", sa.String(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(), index=True, nullable=True),
        sa.Column("telegram_notification_sent", sa.Boolean(), default=False),
        sa.Column("telegram_reminder_scheduled", sa.Boolean(), default=False),
        sa.Column("appointment_date", sa.String(), nullable=True),
        sa.Column("appointment_time", sa.String(), nullable=True),
    )

    op.create_table(
        "counters",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("counter_number", sa.Integer(), unique=True, nullable=False),
        sa.Column("counter_name", sa.String(), nullable=False),
        sa.Column("service_types", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("current_ticket_id", sa.Integer(), nullable=True),
        sa.Column("staff_name", sa.String(), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("citizen_id", sa.Integer(), nullable=True),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("counter_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("is_suspicious", sa.Boolean(), default=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("tickets")
    op.drop_table("counters")
    op.drop_table("citizens")
    op.execute("DROP TYPE IF EXISTS ticketstatus")
    op.execute("DROP TYPE IF EXISTS servicetype")
