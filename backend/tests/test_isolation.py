"""Cross-user isolation tests (docs/SECURITY_AUDIT.md section 11).

The backend's Supabase client always uses the SERVICE-ROLE key
(backend/config.py), which bypasses Postgres RLS entirely -- so the real
isolation boundary at the API layer is each route handler's manual
`.eq("user_id", user_id)` scoping plus the auth middleware, not RLS. These
tests exercise that real boundary. Testing actual RLS policies would mean
hitting PostgREST directly with an anon key + real user JWT (a separate,
out-of-scope piece of infrastructure -- see docs/SECURITY_AUDIT.md).

Uses GET/PUT /categories/ rather than /dashboard/reports for the read/write
cases: categories rows don't require the transactions translation pipeline
(which can call out to a real translation API), so these stay fast,
deterministic, and network-free while still exercising the same
`.eq("user_id", ...)` pattern used throughout the app.
"""

USER_A = "user-a-id"
USER_B = "user-b-id"


def _headers(make_token, sub):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_user_b_cannot_read_user_a_categories(client, patch_jwks, make_token, fake_db):
    fake_db.seed(
        "categories",
        [
            {"id": "cat-a1", "user_id": USER_A, "name": "Groceries"},
            {"id": "cat-b1", "user_id": USER_B, "name": "Transport"},
        ],
    )

    response = client.get("/categories/", headers=_headers(make_token, USER_B))

    assert response.status_code == 200
    names = {c["name"] for c in response.json()["categories"]}
    assert names == {"Transport"}


def test_user_a_can_read_own_categories(client, patch_jwks, make_token, fake_db):
    """Sanity check that the fake DB isn't just returning nothing for
    everyone -- proves the previous test's empty result means real
    filtering, not a broken fake."""
    fake_db.seed(
        "categories",
        [
            {"id": "cat-a1", "user_id": USER_A, "name": "Groceries"},
            {"id": "cat-b1", "user_id": USER_B, "name": "Transport"},
        ],
    )

    response = client.get("/categories/", headers=_headers(make_token, USER_A))

    assert response.status_code == 200
    names = {c["name"] for c in response.json()["categories"]}
    assert names == {"Groceries"}


def test_user_b_cannot_update_user_a_category(client, patch_jwks, make_token, fake_db):
    fake_db.seed(
        "categories",
        [{"id": "cat-a1", "user_id": USER_A, "name": "Groceries"}],
    )

    response = client.put(
        "/categories/cat-a1",
        json={"name": "Hacked"},
        headers=_headers(make_token, USER_B),
    )

    assert response.status_code == 404
    stored = fake_db._tables["categories"].rows[0]
    assert stored["name"] == "Groceries"


def test_user_b_delete_account_only_affects_b(client, patch_jwks, make_token, fake_db):
    response = client.delete("/settings/account", headers=_headers(make_token, USER_B))

    assert response.status_code == 200
    assert fake_db.auth.admin.deleted_user_ids == [USER_B]
    assert USER_A not in fake_db.auth.admin.deleted_user_ids
