def create_sale(client, user_id="john_doe", brand="brand_1", earning="40"):
    resp = client.post("/sales", json={"userId": user_id, "brand": brand, "earning": earning})
    assert resp.status_code == 201
    return resp.json()


def test_approved_sale_pays_earning_minus_advance(client, john):
    # PDF Case 1: earning=30, advance=3 -> approved remainder = 27
    sale = create_sale(client, earning="30")
    client.post("/jobs/advance-payout")

    resp = client.post(f"/admin/sales/{sale['id']}/reconcile", json={"decision": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "30.00"  # 3 advance + 27 final payout


def test_rejected_sale_claws_back_the_advance(client, john):
    # PDF Case 2: earning=50, advance=5 -> rejected adjustment = -5
    sale = create_sale(client, earning="50")
    client.post("/jobs/advance-payout")

    resp = client.post(f"/admin/sales/{sale['id']}/reconcile", json={"decision": "rejected"})
    assert resp.status_code == 200

    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "0.00"  # 5 advance - 5 clawback


def test_reconciling_an_already_reconciled_sale_is_rejected(client, john):
    sale = create_sale(client, earning="40")
    client.post("/jobs/advance-payout")
    client.post(f"/admin/sales/{sale['id']}/reconcile", json={"decision": "approved"})

    second_attempt = client.post(f"/admin/sales/{sale['id']}/reconcile", json={"decision": "rejected"})
    assert second_attempt.status_code == 409

    # Balance must be unaffected by the rejected duplicate reconciliation.
    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "40.00"


def test_full_worked_example_from_assignment_pdf(client, john):
    """
    Three brand_1 sales of ₹40 each. One rejected, two approved.

    The PDF's "Total Final Payout = ₹68" is the sum of the *reconciliation-time
    adjustments only* (-4 + 36 + 36) — it does not include the ₹12 advance the
    user already received earlier. The user's actual running balance is the
    advance plus those adjustments: 12 + 68 = 80, which is exactly their true
    entitlement (two ₹40 sales approved, one rejected) — confirming the ledger
    never over- or under-pays across the two stages.
    """
    sales = [create_sale(client, earning="40") for _ in range(3)]

    job_result = client.post("/jobs/advance-payout").json()
    assert len(job_result["paidSaleIds"]) == 3

    client.post(f"/admin/sales/{sales[0]['id']}/reconcile", json={"decision": "rejected"})
    client.post(f"/admin/sales/{sales[1]['id']}/reconcile", json={"decision": "approved"})
    client.post(f"/admin/sales/{sales[2]['id']}/reconcile", json={"decision": "approved"})

    ledger = client.get("/users/john_doe/ledger").json()
    reconciliation_entries = [e for e in ledger if e["type"] in ("FINAL_PAYOUT", "ADJUSTMENT")]
    total_final_payout = sum(float(e["amount"]) for e in reconciliation_entries)
    assert total_final_payout == 68.0  # matches the PDF's worked example exactly

    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "80.00"  # advance (12) + final payout (68) = true entitlement
