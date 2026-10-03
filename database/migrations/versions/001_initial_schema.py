"""Initial schema — services, incidents, audit_logs

Revision ID: 001
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Services table
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("health_endpoint", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN",
                name="servicestatus",
            ),
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("version", sa.String(64), nullable=True),
        sa.Column(
            "last_health_check",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_services_name", "services", ["name"])

    # Incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(64), nullable=False),
        sa.Column("service", sa.String(255), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "LOW", "MEDIUM", "HIGH", "CRITICAL",
                name="incidentseverity",
            ),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum(
                "HIGH_ERROR_RATE", "HIGH_LATENCY", "SERVICE_DOWN",
                "POD_CRASH_LOOP", "DATABASE_FAILURE", "API_SCHEMA_CHANGE",
                "DEPLOYMENT_FAILURE", "RESOURCE_EXHAUSTION",
                name="incidenttype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DETECTED", "INVESTIGATING", "ROOT_CAUSE_IDENTIFIED",
                "REMEDIATION_PROPOSED", "AWAITING_APPROVAL",
                "REMEDIATING", "VERIFYING", "RESOLVED", "FAILED",
                "ESCALATED",
                name="incidentstatus",
            ),
            nullable=False,
            server_default="DETECTED",
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index("ix_incidents_incident_id", "incidents", ["incident_id"])
    op.create_index("ix_incidents_service", "incidents", ["service"])

    # Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("incident_id", sa.String(64), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index(
        "ix_audit_logs_incident_id", "audit_logs", ["incident_id"]
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("incidents")
    op.drop_table("services")

    # Drop enums (PostgreSQL-specific)
    op.execute("DROP TYPE IF EXISTS incidentstatus")
    op.execute("DROP TYPE IF EXISTS incidenttype")
    op.execute("DROP TYPE IF EXISTS incidentseverity")
    op.execute("DROP TYPE IF EXISTS servicestatus")
