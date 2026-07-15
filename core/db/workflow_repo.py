"""Workflow / scenario repository — workflows table."""
from core.logger import get_logger

logger = get_logger(__name__)


class WorkflowRepo:
    def __init__(self, conn):
        self.conn = conn

    def create_workflow(self, user_id, name, data):
        c = self.conn.cursor()
        try:
            c.execute(
                'INSERT INTO workflows (user_id, name, data, created_at, updated_at)'
                ' VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
                (user_id, name, data),
            )
            wf_id = c.lastrowid
            self.conn.commit()
            return wf_id
        finally:
            pass

    def get_scenarios(self, user_id):
        c = self.conn.cursor()
        try:
            c.execute(
                'SELECT id, name, description, updated_at, data FROM workflows'
                ' WHERE user_id = ? ORDER BY updated_at DESC',
                (user_id,),
            )
            return [
                {
                    'id': row['id'], 'name': row['name'],
                    'description': row['description'], 'updated_at': row['updated_at'],
                    'data': row['data'], 'steps': row['data'],
                }
                for row in c.fetchall()
            ]
        except Exception as e:
            logger.error("Error fetching scenarios for user %s: %s", user_id, e, exc_info=True)
            return []

    def get_scenario(self, scenario_id, user_id):
        c = self.conn.cursor()
        c.execute(
            'SELECT id, name, description, updated_at, data, user_id FROM workflows'
            ' WHERE id = ? AND user_id = ?',
            (scenario_id, user_id),
        )
        row = c.fetchone()
        if row:
            return {
                'id': row['id'], 'name': row['name'],
                'description': row['description'], 'updated_at': row['updated_at'],
                'data': row['data'], 'steps': row['data'], 'user_id': row['user_id'],
            }
        return None

    def create_scenario(self, user_id, name, description, active, steps):
        c = self.conn.cursor()
        try:
            c.execute(
                'INSERT INTO workflows (user_id, name, description, data, created_at, updated_at)'
                ' VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
                (user_id, name, description, steps),
            )
            scenario_id = c.lastrowid
            self.conn.commit()
            return scenario_id
        finally:
            pass

    def update_scenario(self, scenario_id, user_id, data):
        c = self.conn.cursor()
        updates, values = [], []
        if data.get('name') is not None:
            updates.append("name = ?"); values.append(data['name'])
        if data.get('description') is not None:
            updates.append("description = ?"); values.append(data['description'])
        if data.get('steps') is not None:
            updates.append("data = ?"); values.append(data['steps'])
        if not updates:
            return
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE workflows SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        values.extend([scenario_id, user_id])
        c.execute(query, tuple(values))
        self.conn.commit()

    def delete_scenario(self, scenario_id, user_id):
        c = self.conn.cursor()
        c.execute(
            "DELETE FROM workflows WHERE id = ? AND user_id = ?",
            (scenario_id, user_id),
        )
        self.conn.commit()
