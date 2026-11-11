"""Sign-in, sessions, roles and attribution (SRS USR-1 to USR-4), through the API."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import auth, manage, models, security
from app.config import settings
from app.main import app

from .conftest import ADMIN_EMAIL, OPERATOR_EMAIL, ORIGIN, PASSWORD, iso, make_user, sign_in

# The only routes that answer without a session.
PUBLIC_PATHS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/logout",
}


def _operations():
    """Every (method, path) the API offers, with path parameters filled in."""
    for path, methods in app.openapi()["paths"].items():
        concrete = (
            path.replace("{bag_id}", "SUBREC-0001")
            .replace("{run_id}", "1")
            .replace("{species_id}", "1")
            .replace("{grain_type_id}", "1")
            .replace("{user_id}", "1")
            .replace("{lot_id}", "1")
            .replace("{code}", "lions_mane")
        )
        # Any other identifier in a path is a number.
        concrete = re.sub(r"\{[a-z_]+_id\}", "1", concrete)
        assert "{" not in concrete, f"add a sample value for {path}"
        for method in methods:
            yield method.upper(), path, concrete


# ---------------------------------------------------------------- USR-1

def test_every_route_but_health_and_sign_in_needs_a_session(anon_client):
    checked = 0
    for method, path, concrete in _operations():
        response = anon_client.request(method, concrete, json={})
        if path in PUBLIC_PATHS:
            assert response.status_code != 401, f"{method} {path} should be public"
        else:
            assert response.status_code == 401, f"{method} {path} answered {response.status_code} without a session"
            assert response.json()["detail"] == "Sign in to continue."
            checked += 1
    assert checked >= 45


def test_health_checks_answer_without_a_session(anon_client):
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/health/live").status_code == 200
    assert anon_client.get("/api/health/ready").status_code in (200, 503)


def test_nothing_is_served_under_the_namespace_reserved_for_the_website():
    """Brief section 10: /api/integration/ belongs to the website's read-only API (WP-9)."""
    assert [p for p in app.openapi()["paths"] if p.startswith("/api/integration")] == []


def test_production_does_not_serve_the_api_documentation():
    """Run in a fresh interpreter: the setting is read when the app is built."""
    import subprocess
    import sys

    code = (
        "from fastapi.testclient import TestClient; from app.main import app; c = TestClient(app); "
        "print([c.get(p).status_code for p in ('/docs', '/redoc', '/openapi.json', '/api/health')])"
    )
    for env_name, expected in (("production", "[404, 404, 404, 200]"), ("development", "[200, 200, 200, 200]")):
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env={"DATABASE_URL": "sqlite://", "APP_ENV": env_name, "PATH": ""},
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
        )
        assert result.stdout.strip() == expected, result.stderr[-400:]


def test_a_request_is_recognised_through_one_list_of_authenticators():
    """The seam for a second credential type: service tokens are added to this list."""
    assert [fn.__name__ for fn in auth.AUTHENTICATORS] == ["_user_from_session_cookie"]


# ---------------------------------------------------------------- USR-3: sign-in

def test_sign_in_sets_an_http_only_same_site_cookie_and_returns_the_user(anon_client, admin_user):
    response = anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    assert response.json() == {
        "user_id": admin_user.user_id,
        "email": ADMIN_EMAIL,
        "display_name": "Ada Admin",
        "role": "admin",
        "must_change_password": False,
    }
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{settings.session_cookie_name}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    # Plain HTTP in this test, so the cookie cannot be marked Secure.
    assert "Secure" not in cookie

    assert anon_client.get("/api/auth/me").json()["email"] == ADMIN_EMAIL


def test_the_cookie_is_marked_secure_when_the_request_came_over_https(anon_client, admin_user):
    response = anon_client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_email_is_matched_without_regard_to_case_or_spaces(anon_client, admin_user):
    response = anon_client.post("/api/auth/login", json={"email": "  Admin@Example.COM ", "password": PASSWORD})
    assert response.status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_answer(anon_client, admin_user):
    wrong = anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "not the password"})
    unknown = anon_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "The email or password is not right."}
    assert "set-cookie" not in wrong.headers
    assert anon_client.get("/api/auth/me").status_code == 401


def test_passwords_are_stored_as_bcrypt_hashes_and_tokens_as_digests(db_session, anon_client, admin_user):
    assert admin_user.password_hash.startswith("$2b$")
    assert PASSWORD not in admin_user.password_hash

    sign_in(anon_client, ADMIN_EMAIL)
    token = anon_client.cookies.get(settings.session_cookie_name)
    assert len(token) >= 43  # 32 random bytes, URL-safe

    session = db_session.query(models.UserSession).one()
    assert session.token_hash == security.token_digest(token)
    assert token not in (session.token_hash, session.user_agent or "", session.ip_address or "")


def test_a_deactivated_user_cannot_sign_in(db_session, anon_client, operator_user):
    operator_user.is_active = False
    db_session.commit()
    response = anon_client.post("/api/auth/login", json={"email": OPERATOR_EMAIL, "password": PASSWORD})
    assert response.status_code == 401


# ---------------------------------------------------------------- USR-3: sessions end

def test_sign_out_ends_the_session_on_the_server(api, db_session, admin_user):
    browser = sign_in(api(), ADMIN_EMAIL)
    token = browser.cookies.get(settings.session_cookie_name)

    assert browser.post("/api/auth/logout").status_code == 204
    assert browser.get("/api/auth/me").status_code == 401
    assert db_session.query(models.UserSession).count() == 0

    # A copy of the old cookie is worth nothing.
    thief = api()
    thief.cookies.set(settings.session_cookie_name, token)
    assert thief.get("/api/auth/me").status_code == 401

    # Signing out when not signed in is not an error.
    assert api().post("/api/auth/logout").status_code == 204


def test_a_session_ends_after_the_idle_period(db_session, client):
    session = db_session.query(models.UserSession).one()
    session.last_seen_at = datetime.now(timezone.utc) - timedelta(days=settings.session_idle_days, minutes=1)
    db_session.commit()

    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/bags").status_code == 401
    assert db_session.query(models.UserSession).count() == 0


def test_a_session_ends_at_its_absolute_limit_even_when_in_use(db_session, client):
    session = db_session.query(models.UserSession).one()
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.last_seen_at = datetime.now(timezone.utc)
    db_session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_use_keeps_a_session_alive(db_session, client):
    session = db_session.query(models.UserSession).one()
    almost_idle = datetime.now(timezone.utc) - timedelta(days=settings.session_idle_days - 1)
    session.last_seen_at = almost_idle
    db_session.commit()

    assert client.get("/api/auth/me").status_code == 200
    db_session.refresh(session)
    assert auth._aware(session.last_seen_at) > almost_idle + timedelta(days=1)


def test_deactivating_a_user_ends_their_sessions_at_once(client, operator_client, operator_user):
    assert operator_client.get("/api/auth/me").status_code == 200
    response = client.patch(f"/api/users/{operator_user.user_id}", json={"is_active": False})
    assert response.status_code == 200 and response.json()["is_active"] is False
    assert operator_client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------- USR-3: rate limit

def test_sign_in_is_refused_after_too_many_failures_for_one_email(db_session, anon_client, admin_user):
    for _ in range(settings.login_max_failures_per_email):
        assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}).status_code == 401

    blocked = anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert blocked.status_code == 429
    assert "Too many failed sign-in attempts" in blocked.json()["detail"]
    assert int(blocked.headers["retry-after"]) == settings.login_window_minutes * 60

    # Another person is not locked out by it.
    make_user(db_session, "other@example.com", "operator")
    assert anon_client.post("/api/auth/login", json={"email": "other@example.com", "password": PASSWORD}).status_code == 200


def test_the_limit_lifts_when_the_window_has_passed(db_session, anon_client, admin_user):
    for _ in range(settings.login_max_failures_per_email):
        anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 429

    long_ago = datetime.now(timezone.utc) - timedelta(minutes=settings.login_window_minutes + 1)
    db_session.query(models.LoginAttempt).update({models.LoginAttempt.attempted_at: long_ago})
    db_session.commit()
    assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200


def test_a_successful_sign_in_clears_the_count(anon_client, admin_user):
    for _ in range(settings.login_max_failures_per_email - 1):
        anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200
    for _ in range(settings.login_max_failures_per_email - 1):
        assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}).status_code == 401
    assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200


def test_one_address_guessing_at_many_emails_is_refused(anon_client, admin_user):
    for attempt in range(settings.login_max_failures_per_ip):
        response = anon_client.post(
            "/api/auth/login", json={"email": f"guess{attempt}@example.com", "password": "wrong"}
        )
        assert response.status_code == 401
    assert anon_client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 429


# ---------------------------------------------------------------- SEC-1

def test_in_production_a_password_is_not_accepted_over_plain_http_from_the_internet(
    api, admin_user, monkeypatch
):
    monkeypatch.setattr(settings, "app_env", "production")
    internet = TestClient(app, headers={"Origin": ORIGIN}, client=("8.8.8.8", 40000))
    refused = internet.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert refused.status_code == 403
    assert "encrypted connection" in refused.json()["detail"]

    # The same request through the proxy's HTTPS listener is accepted.
    accepted = internet.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert accepted.status_code == 200

    # The server itself and a private address may use plain HTTP (deploy checks, SSH tunnel).
    for address in ("127.0.0.1", "172.18.0.5"):
        local = TestClient(app, headers={"Origin": ORIGIN}, client=(address, 40000))
        assert local.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200


# ---------------------------------------------------------------- origin check

def test_a_state_changing_request_must_come_from_the_app(api, db_session, admin_user):
    browser = sign_in(TestClient(app, headers={"Origin": ORIGIN}), ADMIN_EMAIL)
    cookies = {settings.session_cookie_name: browser.cookies.get(settings.session_cookie_name)}
    body = {"name": "Wheat"}

    def post(headers):
        return TestClient(app, cookies=cookies, headers=headers).post("/api/grain-types", json=body)

    assert post({"Origin": "https://evil.example"}).status_code == 403
    assert post({}).status_code == 403
    assert post({"Origin": "null"}).status_code == 403
    assert post({"Referer": "https://evil.example/page"}).status_code == 403
    assert db_session.query(models.GrainType).count() == 0

    assert post({"Referer": "http://testserver/grain-types"}).status_code == 200
    # An origin listed in CORS_ORIGINS (the development frontend) is trusted.
    assert post({"Origin": "http://localhost:3000"}).status_code == 409  # same name again: got past the check


def test_the_browsers_host_behind_the_proxy_counts_as_the_apps_own(api, admin_user, monkeypatch):
    proxied = TestClient(app, headers={"Origin": "https://app.farm.example", "X-Forwarded-Host": "app.farm.example"})
    assert proxied.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200

    monkeypatch.setattr(settings, "app_hostname", "app.themauryrivermushroomfarm.com")
    named = TestClient(app, headers={"Origin": "https://app.themauryrivermushroomfarm.com"})
    assert named.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200


def test_reading_needs_no_origin(api, admin_user):
    browser = sign_in(TestClient(app, headers={"Origin": ORIGIN}), ADMIN_EMAIL)
    cookies = {settings.session_cookie_name: browser.cookies.get(settings.session_cookie_name)}
    assert TestClient(app, cookies=cookies).get("/api/bags").status_code == 200


# ---------------------------------------------------------------- USR-3: first administrator

def test_nobody_can_sign_in_until_an_administrator_exists(anon_client):
    assert anon_client.get("/api/auth/status").json() == {"setup_required": True}
    response = anon_client.post("/api/auth/login", json={"email": "anyone@example.com", "password": PASSWORD})
    assert response.status_code == 401
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/dashboard/overview").status_code == 401


def test_first_administrator_is_created_from_configuration_once(db_session, anon_client):
    assert auth.ensure_bootstrap_admin(db_session, "", "") == "missing"
    assert auth.ensure_bootstrap_admin(db_session, "Owner@Example.com", "a long first password") == "created"
    assert anon_client.get("/api/auth/status").json() == {"setup_required": False}

    owner = db_session.query(models.User).one()
    assert (owner.email, owner.display_name, owner.role, owner.is_active, owner.must_change_password) == (
        "owner@example.com",
        "Owner",
        "admin",
        True,
        True,
    )
    signed_in = anon_client.post("/api/auth/login", json={"email": "owner@example.com", "password": "a long first password"})
    assert signed_in.json()["must_change_password"] is True

    # A second call never adds or changes anyone, whatever it is given.
    assert auth.ensure_bootstrap_admin(db_session, "intruder@example.com", "another long password") == "exists"
    assert db_session.query(models.User).count() == 1


def test_a_weak_first_password_is_refused(db_session):
    with pytest.raises(security.PasswordPolicyError):
        auth.ensure_bootstrap_admin(db_session, "owner@example.com", "short")
    assert db_session.query(models.User).count() == 0


# ---------------------------------------------------------------- change password

def test_change_password(api, db_session, admin_user):
    this_browser = sign_in(api(), ADMIN_EMAIL)
    other_browser = sign_in(api(), ADMIN_EMAIL)
    admin_user.must_change_password = True
    db_session.commit()

    wrong = this_browser.post(
        "/api/auth/change-password", json={"current_password": "nope", "new_password": "a brand new password"}
    )
    assert wrong.status_code == 400 and wrong.json()["detail"] == "The current password is not right."

    for weak, reason in (
        ("short", "at least 10 characters"),
        (PASSWORD, "different from the current one"),
        (ADMIN_EMAIL, "same as the email"),
        ("x" * 73, "at most 72 characters"),
    ):
        refused = this_browser.post(
            "/api/auth/change-password", json={"current_password": PASSWORD, "new_password": weak}
        )
        assert refused.status_code == 400 and reason in refused.json()["detail"], weak

    changed = this_browser.post(
        "/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "a brand new password"}
    )
    assert changed.status_code == 200 and changed.json()["must_change_password"] is False

    # This browser stays signed in; every other one is signed out.
    assert this_browser.get("/api/auth/me").status_code == 200
    assert other_browser.get("/api/auth/me").status_code == 401
    assert api().post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 401
    assert api().post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "a brand new password"}).status_code == 200


def test_a_user_can_change_the_name_shown_for_them(operator_client, operator_user):
    renamed = operator_client.patch("/api/auth/me", json={"display_name": "  Oliver Operator  "})
    assert renamed.status_code == 200 and renamed.json()["display_name"] == "Oliver Operator"
    assert operator_client.get("/api/auth/me").json()["display_name"] == "Oliver Operator"
    assert operator_client.patch("/api/auth/me", json={"display_name": "   "}).status_code == 400
    # Nothing else about the account can be changed this way.
    operator_client.patch("/api/auth/me", json={"display_name": "Oliver", "role": "admin"})
    assert operator_client.get("/api/auth/me").json()["role"] == "operator"


# ---------------------------------------------------------------- USR-2: roles

ADMIN_ONLY_WRITES = [
    ("POST", "/api/species", {"code": "BO", "name": "Blue Oyster"}),
    ("PATCH", "/api/species/1", {"name": "Renamed"}),
    ("POST", "/api/grain-types", {"name": "Millet"}),
    ("PATCH", "/api/grain-types/1", {"notes": "x"}),
    ("POST", "/api/fill-profiles", {"name": "Big", "target_dry_kg_per_bag": 2, "target_water_kg_per_bag": 2}),
    ("POST", "/api/ingredients", {"name": "Gypsum"}),
    ("GET", "/api/users", None),
    ("POST", "/api/users", {"email": "new@example.com", "display_name": "New", "password": PASSWORD}),
    ("PATCH", "/api/users/1", {"display_name": "Changed"}),
]


@pytest.mark.parametrize("method, path, body", ADMIN_ONLY_WRITES)
def test_an_operator_is_refused_what_only_an_administrator_may_do(farm, operator_client, method, path, body):
    response = operator_client.request(method, path, json=body)
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Only an administrator can do that."


@pytest.mark.parametrize("method, path, body", ADMIN_ONLY_WRITES)
def test_an_administrator_may(farm, method, path, body):
    response = farm.client.request(method, path, json=body)
    assert response.status_code in (200, 201), response.text


def test_an_operator_can_do_the_production_work_and_read_the_reports(farm, operator_client, operator_user):
    """Runs, bags, inputs, events and reports are open to an operator (USR-2)."""
    work = farm.as_user(operator_client)

    mix_lot = work.post(
        "/api/mix-lots",
        {
            "lot_code": "LOT-OP",
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "fill_profile_id": farm.fill_profile["fill_profile_id"],
        },
    )
    culture = work.post("/api/liquid-cultures", {"culture_code": "LC-OP", "species_id": farm.species["species_id"]})
    assert mix_lot["lot_code"] == "LOT-OP" and culture["culture_code"] == "LC-OP"

    run, bags = work.inoculated_substrate_bags(bag_count=2)
    first = bags[0]["bag_id"]
    work.post(f"/api/bags/{first}/incubation-start")
    work.post(f"/api/bags/{first}/ready")
    work.post(f"/api/bags/{first}/fruiting-start")
    work.post("/api/harvest-events", {"bag_id": first, "flush_number": 1, "fresh_weight_kg": 0.5})
    work.post(f"/api/bags/{bags[1]['bag_id']}/disposal", {"disposal_reason": "CONTAMINATION"})

    assert work.get("/api/reports/production")["summary"]["total_substrate_bags"] == 2
    assert work.get("/api/dashboard/overview")["summary"]["total_contaminated_bags"] == 1
    assert work.get(f"/api/pasteurization-runs/{run['pasteurization_run_id']}/detail")["summary"]["total_bags"] == 2


# ---------------------------------------------------------------- USR-4: attribution

def test_each_event_records_who_entered_it(farm, operator_client, operator_user):
    run, bags = farm.inoculated_substrate_bags(bag_count=1)  # entered by the administrator
    bag_id = bags[0]["bag_id"]
    for step in ("incubation-start", "ready", "fruiting-start"):
        assert operator_client.post(f"/api/bags/{bag_id}/{step}").status_code == 200
    harvest = operator_client.post(
        "/api/harvest-events", json={"bag_id": bag_id, "flush_number": 1, "fresh_weight_kg": 0.4}
    )
    assert harvest.status_code == 200 and harvest.json()["recorded_by_name"] == "Olly Operator"

    events = {e["event_type"]: e["recorded_by_name"] for e in farm.get(f"/api/bags/{bag_id}")["status_events"]}
    assert events["INOCULATED"] == "Ada Admin"
    assert events["PASTEURIZED"] == "Ada Admin"
    assert events["INCUBATION_STARTED"] == "Olly Operator"
    assert events["READY"] == "Olly Operator"
    assert events["FRUITING_STARTED"] == "Olly Operator"
    assert events["HARVEST_RECORDED"] == "Olly Operator"


# ---------------------------------------------------------------- user management

def test_administrator_manages_users(api, client, admin_user):
    created = client.post(
        "/api/users",
        json={"email": " Pat@Example.com ", "display_name": " Pat Picker ", "role": "operator", "password": "first password 1"},
    )
    assert created.status_code == 201
    pat = created.json()
    assert (pat["email"], pat["display_name"], pat["role"], pat["is_active"], pat["must_change_password"]) == (
        "pat@example.com",
        "Pat Picker",
        "operator",
        True,
        True,
    )
    assert "password" not in created.text.replace("must_change_password", "")

    duplicate = client.post(
        "/api/users", json={"email": "pat@example.com", "display_name": "Pat Again", "password": "first password 1"}
    )
    assert duplicate.status_code == 409
    weak = client.post("/api/users", json={"email": "weak@example.com", "display_name": "Weak", "password": "short"})
    assert weak.status_code == 400
    bad_email = client.post("/api/users", json={"email": "not-an-email", "display_name": "X", "password": "first password 1"})
    assert bad_email.status_code == 422

    assert [u["email"] for u in client.get("/api/users").json()] == [ADMIN_EMAIL, "pat@example.com"]

    pats_browser = sign_in(api(), "pat@example.com", "first password 1")
    promoted = client.patch(f"/api/users/{pat['user_id']}", json={"role": "admin"})
    assert promoted.json()["role"] == "admin"
    assert pats_browser.get("/api/users").status_code == 200  # the new role applies at once

    # A password reset signs the user out everywhere and asks for a new password at next sign-in.
    reset = client.patch(f"/api/users/{pat['user_id']}", json={"password": "second password 2"})
    assert reset.status_code == 200 and reset.json()["must_change_password"] is True
    assert pats_browser.get("/api/auth/me").status_code == 401
    assert api().post("/api/auth/login", json={"email": "pat@example.com", "password": "second password 2"}).status_code == 200

    assert client.patch("/api/users/9999", json={"display_name": "Ghost"}).status_code == 404


def test_the_last_administrator_cannot_be_removed(client, admin_user, operator_user):
    for change in ({"role": "operator"}, {"is_active": False}):
        response = client.patch(f"/api/users/{admin_user.user_id}", json=change)
        assert response.status_code == 400
        assert "own administrator access" in response.json()["detail"]

    # With a second administrator, each still cannot remove their own access, but can remove the other's.
    client.patch(f"/api/users/{operator_user.user_id}", json={"role": "admin"})
    assert client.patch(f"/api/users/{admin_user.user_id}", json={"is_active": False}).status_code == 400
    assert client.patch(f"/api/users/{operator_user.user_id}", json={"role": "operator"}).status_code == 200


# ---------------------------------------------------------------- server commands

@pytest.fixture
def manage_db(db_session, monkeypatch):
    """Point app.manage at the test database."""
    factory = sessionmaker(bind=db_session.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(manage, "SessionLocal", factory)
    return db_session


def test_bootstrap_admin_command(manage_db, monkeypatch, capsys):
    assert manage.main(["bootstrap-admin"]) == 0
    assert "Nobody can sign in yet" in capsys.readouterr().out

    monkeypatch.setattr(settings, "bootstrap_admin_email", "owner@example.com")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "short")
    assert manage.main(["bootstrap-admin"]) == 2

    monkeypatch.setattr(settings, "bootstrap_admin_password", "the first long password")
    assert manage.main(["bootstrap-admin"]) == 0
    output = capsys.readouterr()
    assert "first administrator created" in output.out
    assert "the first long password" not in output.out + output.err

    assert manage.main(["bootstrap-admin"]) == 0
    assert "nothing to do" in capsys.readouterr().out
    manage_db.expire_all()
    assert manage_db.query(models.User).count() == 1


def test_smoke_session_command_gives_a_short_lived_session(manage_db, api, admin_user, capsys):
    assert manage.main(["smoke-session"]) == 0
    token = capsys.readouterr().out.strip()

    browser = api()
    browser.cookies.set(settings.session_cookie_name, token)
    assert browser.get("/api/auth/me").json()["email"] == ADMIN_EMAIL

    manage_db.expire_all()
    session = manage_db.query(models.UserSession).one()
    remaining = auth._aware(session.expires_at) - datetime.now(timezone.utc)
    assert timedelta(0) < remaining <= timedelta(minutes=2)


def test_smoke_session_command_without_an_administrator(manage_db, capsys):
    assert manage.main(["smoke-session"]) == 3
    assert capsys.readouterr().out == ""


def test_reset_password_command(manage_db, api, client, admin_user, monkeypatch, capsys):
    assert manage.main(["reset-password", "--email", ADMIN_EMAIL]) == 2  # NEW_PASSWORD not set

    monkeypatch.setenv("NEW_PASSWORD", "recovered password 9")
    assert manage.main(["reset-password", "--email", "nobody@example.com"]) == 3
    assert manage.main(["reset-password", "--email", ADMIN_EMAIL]) == 0
    assert "recovered password 9" not in capsys.readouterr().out

    manage_db.expire_all()
    assert client.get("/api/auth/me").status_code == 401  # signed out everywhere
    recovered = api().post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "recovered password 9"})
    assert recovered.status_code == 200 and recovered.json()["must_change_password"] is True
