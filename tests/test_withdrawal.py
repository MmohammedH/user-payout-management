from datetime import timedelta

from app.models import Withdrawal, _utcnow


def create_sale(client, user_id="john_doe", brand="brand_1", earning="100"):
    resp = client.post("/sales", json={"userId": user_id, "brand": brand, "earning": earning})
    assert resp.status_code == 201
    return resp.json()


def fund_user(client, earning="100"):
    """Approve a sale outright so the user has a spendable balance."""
    sale = create_sale(client, earning=earning)
    client.post(f"/admin/sales/{sale['id']}/reconcile", json={"decision": "approved"})


def test_withdrawal_succeeds_within_available_balance(client, john):
    fund_user(client, earning="100")

    resp = client.post("/users/john_doe/withdrawals", json={"amount": "40"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "initiated"

    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "60.00"


def test_withdrawal_rejects_amount_over_balance(client, john):
    fund_user(client, earning="100")

    resp = client.post("/users/john_doe/withdrawals", json={"amount": "500"})
    assert resp.status_code == 400


def test_second_withdrawal_within_24h_is_blocked(client, john):
    fund_user(client, earning="100")

    first = client.post("/users/john_doe/withdrawals", json={"amount": "10"})
    assert first.status_code == 201

    second = client.post("/users/john_doe/withdrawals", json={"amount": "10"})
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_withdrawal_allowed_again_after_24h(client, john, db_session):
    fund_user(client, earning="100")

    first = client.post("/users/john_doe/withdrawals", json={"amount": "10"})
    assert first.status_code == 201

    # Time-travel the first withdrawal's timestamp back past the cooldown window.
    withdrawal = db_session.get(Withdrawal, first.json()["id"])
    withdrawal.created_at = _utcnow() - timedelta(hours=24, minutes=1)
    db_session.commit()

    second = client.post("/users/john_doe/withdrawals", json={"amount": "10"})
    assert second.status_code == 201


def test_failed_withdrawal_credits_balance_back_and_unblocks_retry(client, john):
    fund_user(client, earning="100")

    withdrawal = client.post("/users/john_doe/withdrawals", json={"amount": "30"}).json()
    balance_after_debit = client.get("/users/john_doe/balance").json()["balance"]
    assert balance_after_debit == "70.00"

    webhook = client.post(
        "/webhooks/payout-status",
        json={"withdrawalId": withdrawal["id"], "status": "failed"},
    )
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "failed"

    balance_after_reversal = client.get("/users/john_doe/balance").json()["balance"]
    assert balance_after_reversal == "100.00"  # fully restored

    # A failed payout must not count against the 24h cooldown.
    retry = client.post("/users/john_doe/withdrawals", json={"amount": "30"})
    assert retry.status_code == 201


def test_duplicate_failure_webhook_does_not_double_credit(client, john):
    fund_user(client, earning="100")
    withdrawal = client.post("/users/john_doe/withdrawals", json={"amount": "30"}).json()

    client.post("/webhooks/payout-status", json={"withdrawalId": withdrawal["id"], "status": "failed"})
    client.post("/webhooks/payout-status", json={"withdrawalId": withdrawal["id"], "status": "failed"})

    balance = client.get("/users/john_doe/balance").json()["balance"]
    assert balance == "100.00"  # not 130 — the reversal only ever applies once
