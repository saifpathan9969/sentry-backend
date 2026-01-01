"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_tier enum
    op.execute("CREATE TYPE user_tier AS ENUM ('free', 'premium', 'enterprise')")
    
    # Create scan_mode enum
    op.execute("CREATE TYPE scan_mode AS ENUM ('common', 'fast', 'full')")
    
    # Create scan_status enum
    op.execute("CREATE TYPE scan_status AS ENUM ('queued', 'running', 'completed', 'failed')")
    
    # Create subscription_tier enum
    op.execute("CREATE TYPE subscription_tier AS ENUM ('premium', 'enterprise')")
    
    # Create subscription_status enum
    op.execute("CREATE TYPE subscription_status AS ENUM ('active', 'canceled', 'past_due')")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('tier', postgresql.ENUM('free', 'premium', 'enterprise', name='user_tier'), nullable=False),
        sa.Column('api_key_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_api_key_hash'), 'users', ['api_key_hash'], unique=True)
    op.create_index(op.f('ix_users_tier'), 'users', ['tier'], unique=False)
    
    # Create scans table
    op.create_table(
        'scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target', sa.String(length=500), nullable=False),
        sa.Column('scan_mode', postgresql.ENUM('common', 'fast', 'full', name='scan_mode'), nullable=False),
        sa.Column('status', postgresql.ENUM('queued', 'running', 'completed', 'failed', name='scan_status'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('vulnerabilities_found', sa.Integer(), nullable=False),
        sa.Column('critical_count', sa.Integer(), nullable=False),
        sa.Column('high_count', sa.Integer(), nullable=False),
        sa.Column('medium_count', sa.Integer(), nullable=False),
        sa.Column('low_count', sa.Integer(), nullable=False),
        sa.Column('platform_detected', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('report_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('report_text', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scans_id'), 'scans', ['id'], unique=False)
    op.create_index(op.f('ix_scans_user_id'), 'scans', ['user_id'], unique=False)
    op.create_index(op.f('ix_scans_status'), 'scans', ['status'], unique=False)
    op.create_index(op.f('ix_scans_created_at'), 'scans', ['created_at'], unique=False)
    op.create_index('ix_scans_user_created', 'scans', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_scans_user_status_created', 'scans', ['user_id', 'status', 'created_at'], unique=False)
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=False),
        sa.Column('tier', postgresql.ENUM('premium', 'enterprise', name='subscription_tier'), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'canceled', 'past_due', name='subscription_status'), nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    
    # Create api_usage table
    op.create_table(
        'api_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_usage_id'), 'api_usage', ['id'], unique=False)
    op.create_index(op.f('ix_api_usage_user_id'), 'api_usage', ['user_id'], unique=False)
    op.create_index(op.f('ix_api_usage_created_at'), 'api_usage', ['created_at'], unique=False)
    op.create_index('ix_api_usage_user_created', 'api_usage', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_api_usage_user_created', table_name='api_usage')
    op.drop_index(op.f('ix_api_usage_created_at'), table_name='api_usage')
    op.drop_index(op.f('ix_api_usage_user_id'), table_name='api_usage')
    op.drop_index(op.f('ix_api_usage_id'), table_name='api_usage')
    op.drop_table('api_usage')
    
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    op.drop_index('ix_scans_user_status_created', table_name='scans')
    op.drop_index('ix_scans_user_created', table_name='scans')
    op.drop_index(op.f('ix_scans_created_at'), table_name='scans')
    op.drop_index(op.f('ix_scans_status'), table_name='scans')
    op.drop_index(op.f('ix_scans_user_id'), table_name='scans')
    op.drop_index(op.f('ix_scans_id'), table_name='scans')
    op.drop_table('scans')
    
    op.drop_index(op.f('ix_users_tier'), table_name='users')
    op.drop_index(op.f('ix_users_api_key_hash'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE subscription_status")
    op.execute("DROP TYPE subscription_tier")
    op.execute("DROP TYPE scan_status")
    op.execute("DROP TYPE scan_mode")
    op.execute("DROP TYPE user_tier")
