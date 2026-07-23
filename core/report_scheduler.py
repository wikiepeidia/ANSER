"""Background scheduler that actually executes /se/reports's "scheduled
reports" — previously a dead end (row saved to scheduled_reports, nothing
ever read it back out). Runs core.services.operations_service's
run_due_scheduled_reports() on an interval; due-ness (frequency vs
last_sent_at) is checked inside that function, so this loop's own interval
just needs to be frequent enough not to miss the shortest supported
frequency (daily)."""
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from core.logger import get_logger

logger = get_logger(__name__)

_scheduler = None


def start_report_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    def _tick():
        with app.app_context():
            try:
                from core.services.operations_service import run_due_scheduled_reports
                sent = run_due_scheduled_reports()
                if sent:
                    logger.info('[report_scheduler] Sent %d scheduled report(s)', sent)
            except Exception:
                logger.error('[report_scheduler] Tick failed', exc_info=True)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_tick, 'interval', hours=1, id='scheduled_reports_tick',
                        next_run_time=datetime.now())
    _scheduler.start()
    logger.info('[report_scheduler] Started — checking scheduled reports hourly')
    return _scheduler
