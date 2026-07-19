def create_sale(client, user_id="john_doe", brand="brand_1", earning="40"):
    resp = client.post("/sales", json={"userId": user_id, "brand": brand, "earning": earning})
    assert resp.status_code == 201
    return resp.json()


def test_advance_payout_pays_10_percent_of_pending_sales(client, john):
    create_sale(client, earning="40")
    create_sale(client, earning="40")

    result = client.post("/jobs/advance-payout").json()
    assert len(result["paidSaleIds"]) == 2
    assert result["skippedSaleIds"] == []

    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "8.00"  # 10% of 40 + 10% of 40


def test_advance_payout_job_is_idempotent_across_repeated_runs(client, john):
    create_sale(client, earning="40")

    first_run = client.post("/jobs/advance-payout").json()
    assert first_run["paidSaleIds"] != []

    # Running the job again — and again — must never pay the same sale twice.
    second_run = client.post("/jobs/advance-payout").json()
    third_run = client.post("/jobs/advance-payout").json()

    assert second_run["paidSaleIds"] == []
    assert third_run["paidSaleIds"] == []

    balance = client.get("/users/john_doe/balance").json()
    assert balance["balance"] == "4.00"  # still just the one 10% advance


def test_approved_and_reconciled_sales_are_not_re_advanced(client, john):
    sale = create_sale(client, earning="40")
    client.post("/jobs/advance-payout")
    client.post(f"/admin/sales/{sale['id']}/reconcile", json={"decision": "approved"})

    # Sale is no longer pending, so a later job run must ignore it entirely.
    result = client.post("/jobs/advance-payout").json()
    assert sale["id"] not in result["paidSaleIds"]
    assert sale["id"] not in result["skippedSaleIds"]
