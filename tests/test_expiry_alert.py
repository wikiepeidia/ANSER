"""Covers TRACE-07: wiring TRACE-06's existing expiring-batches query into a
real n8n dispatch action (`GET/POST /api/n8n/internal/rag/expiring-alert`)
and the new `workflow_templates/manuf_expiry_alert.json` schedule-triggered
template that consumes it. See .planning/phases/05-ai-services-automation-
completion/05-03-PLAN.md and 05-CONTEXT.md.
"""
import json
import os
from datetime import date, timedelta


def test_expiring_alert_reuses_trace06_query(logged_in_client, client):
    res = logged_in_client.post('/api/material-batches', json={
        'materialCode': 'NVL-004',
        'quantity': 5,
        'expiryDate': (date.today() + timedelta(days=2)).isoformat(),
    })
    assert res.status_code == 200
    code = res.get_json()['code']

    trace06_res = logged_in_client.get('/api/material-batches/expiring?days=7')
    assert trace06_res.status_code == 200
    trace06_batches = trace06_res.get_json()['batches']
    trace06_entry = next(b for b in trace06_batches if b['code'] == code)

    alert_res = client.get('/api/n8n/internal/rag/expiring-alert?days=7')
    assert alert_res.status_code == 200
    body = alert_res.get_json()
    assert body['success'] is True
    assert body['count'] >= 1
    alert_entry = next(b for b in body['batches'] if b['code'] == code)

    assert alert_entry['daysUntilExpiry'] == trace06_entry['daysUntilExpiry']
    assert alert_entry['materialName'] == trace06_entry['materialName']
    assert alert_entry['quantity'] == trace06_entry['quantity']


def test_expiring_alert_days_filter(logged_in_client, client):
    today = date.today()
    res1 = logged_in_client.post('/api/material-batches', json={
        'materialCode': 'NVL-005',
        'quantity': 3,
        'expiryDate': (today + timedelta(days=1)).isoformat(),
    })
    assert res1.status_code == 200
    code_soon = res1.get_json()['code']

    res2 = logged_in_client.post('/api/material-batches', json={
        'materialCode': 'NVL-006',
        'quantity': 2,
        'expiryDate': (today + timedelta(days=10)).isoformat(),
    })
    assert res2.status_code == 200
    code_far = res2.get_json()['code']

    r1 = client.get('/api/n8n/internal/rag/expiring-alert?days=1')
    assert r1.status_code == 200
    codes1 = [b['code'] for b in r1.get_json()['batches']]
    assert code_soon in codes1
    assert code_far not in codes1

    r2 = client.get('/api/n8n/internal/rag/expiring-alert?days=15')
    assert r2.status_code == 200
    codes2 = [b['code'] for b in r2.get_json()['batches']]
    assert code_soon in codes2
    assert code_far in codes2


def test_expiring_alert_defaults_to_7_days(client):
    res = client.get('/api/n8n/internal/rag/expiring-alert')
    assert res.status_code == 200
    body = res.get_json()
    assert body['days'] == 7


def test_workflow_template_expiry_alert_structure():
    fp = os.path.join(
        os.path.dirname(__file__), '..', 'workflow_templates', 'manuf_expiry_alert.json'
    )
    with open(fp, encoding='utf-8') as f:
        data = json.load(f)

    assert data['name'] == 'manuf_expiry_alert'
    assert data['active'] is False

    node_names = {n['name'] for n in data['nodes']}
    assert any(n['type'] == 'n8n-nodes-base.scheduleTrigger' for n in data['nodes'])
    assert any(
        '$env.RAG_BASE_URL' in n.get('parameters', {}).get('url', '')
        and '/expiring-alert' in n.get('parameters', {}).get('url', '')
        for n in data['nodes']
    )
    assert any(
        n.get('parameters', {}).get('url') == '={{ $env.NOTIFY_URL }}' for n in data['nodes']
    )

    for source, spec in data['connections'].items():
        assert source in node_names
        for branch in spec.get('main', []):
            for conn in branch:
                assert conn['node'] in node_names


def test_expiry_alert_template_appears_in_templates_list(logged_in_client):
    res = logged_in_client.get('/api/n8n/templates')
    assert res.status_code == 200
    slugs = [t['slug'] for t in res.get_json()['templates']]
    assert 'manuf_expiry_alert' in slugs
