"""Shared business helpers — imported by route Blueprints and service layer."""
import json
from datetime import datetime

SUBSCRIPTION_PLANS = {
    'monthly':   {'name': 'Monthly',   'days': 30,  'amount': 500000,  'description': 'Monthly plan'},
    'quarterly': {'name': 'Quarterly', 'days': 90,  'amount': 1200000, 'description': 'Quarterly plan'},
    'yearly':    {'name': 'Yearly',    'days': 365, 'amount': 4000000, 'description': 'Yearly plan'},
}


def format_plan_dict(plan_key):
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return None
    return {'key': plan_key, 'name': plan['name'], 'amount': plan['amount'],
            'days': plan['days'], 'description': plan.get('description', '')}


def parse_db_datetime(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return None
    if hasattr(value, 'strftime'):
        return value
    if isinstance(value, str):
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None


def format_display_datetime(value):
    dt = parse_db_datetime(value)
    return dt.strftime('%d/%m/%Y %H:%M') if dt else None


def parse_metadata(raw_value):
    if not raw_value:
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    try:
        return json.loads(raw_value)
    except Exception:
        return {}
