from __future__ import annotations

from tests.conftest import auth_headers, register


# --- Auth (REG / LOGIN) ---
def test_register_and_me(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "alex@example.com"
    assert body["tokens"]["accessToken"]

    headers = {"Authorization": f"Bearer {body['tokens']['accessToken']}"}
    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["name"] == "Alex Chen"


def test_register_validation(client):
    # REG-04: short password
    resp = client.post("/v1/auth/register", json={"name": "A", "email": "a@b.com", "password": "123"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert resp.json()["error"]["details"]["field"] == "password"


def test_register_duplicate_email(client):
    register(client)
    # REG-05: duplicate email
    resp = register(client)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


def test_login_cases(client):
    register(client)
    # LOGIN-05: trims + lowercases email
    ok = client.post("/v1/auth/login", json={"email": "  ALEX@example.com ", "password": "secret123"})
    assert ok.status_code == 200
    # LOGIN-03: unknown email
    nf = client.post("/v1/auth/login", json={"email": "nobody@x.com", "password": "secret123"})
    assert nf.status_code == 404 and nf.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"
    # LOGIN-04: wrong password
    wp = client.post("/v1/auth/login", json={"email": "alex@example.com", "password": "nope"})
    assert wp.status_code == 401 and wp.json()["error"]["code"] == "WRONG_PASSWORD"


def test_requires_auth(client):
    # NAV-01: protected route without token
    resp = client.get("/v1/profile")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# --- Profile (§3) ---
def test_profile_lifecycle(client):
    headers = auth_headers(client)
    # No profile yet -> 404 (LOGIN-02 flow)
    assert client.get("/v1/profile", headers=headers).status_code == 404

    payload = {"name": "Alex", "skills": ["Python", "React"]}
    put = client.put("/v1/profile", json=payload, headers=headers)
    assert put.status_code == 200
    assert put.json()["updatedAt"] > 0

    got = client.get("/v1/profile", headers=headers)
    assert got.status_code == 200
    assert got.json()["skills"] == ["Python", "React"]


def test_cv_extract_polling(client):
    headers = auth_headers(client)
    files = {"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")}
    start = client.post("/v1/profile/extract-cv", files=files, headers=headers)
    assert start.status_code == 202
    task_id = start.json()["taskId"]

    statuses = []
    for _ in range(4):
        r = client.get(f"/v1/profile/extract-cv/{task_id}", headers=headers)
        statuses.append(r.json()["status"])
    assert "processing" in statuses
    assert statuses[-1] == "complete"
    assert r.json()["draft"]["name"]


# --- Goals (§4) + Tracking (§5) ---
def test_goals_and_tracking_progress(client):
    headers = auth_headers(client)

    catalog = client.get("/v1/goal-catalog", headers=headers)
    assert catalog.status_code == 200 and len(catalog.json()) >= 1

    created = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers)
    assert created.status_code == 201
    goal_id = created.json()["id"]

    # NG-02 / GOAL_ALREADY_ADDED
    dup = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "GOAL_ALREADY_ADDED"

    # Confidence updates progress
    client.patch(f"/v1/goals/{goal_id}", json={"confidence": {"skill-react": 5}}, headers=headers)
    progressed = client.get(f"/v1/goals/{goal_id}", headers=headers).json()["progress"]
    assert progressed > 0

    # Toggle a step -> tracking updates
    step = client.put(
        f"/v1/goals/{goal_id}/tracking/modules/skill-react/steps/0",
        json={"completed": True},
        headers=headers,
    )
    assert step.status_code == 200
    assert 0 in step.json()["modules"]["skill-react"]["completedSteps"]


# --- Jobs (§6) + Tailored CV (§7) + Applications (§8) ---
def test_jobs_applications_flow(client):
    headers = auth_headers(client)
    client.put("/v1/profile", json={"name": "Alex", "skills": ["React"]}, headers=headers)
    goal_id = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers).json()["id"]

    jobs = client.get("/v1/jobs", params={"catalogGoalId": "1"}, headers=headers)
    assert jobs.status_code == 200 and jobs.json()["total"] >= 1

    detail = client.get("/v1/jobs/j_101", headers=headers)
    assert "matchScore" in detail.json()

    # Save / unsave (JOB-05/06)
    saved = client.put("/v1/saved-jobs/j_101", json={"goalId": goal_id}, headers=headers)
    assert saved.status_code == 200
    unsave = client.delete("/v1/saved-jobs/j_101", params={"goalId": goal_id}, headers=headers)
    assert unsave.status_code == 204

    # Tailored CV (§7)
    cv = client.post("/v1/tailored-cv/generate", json={"jobId": "j_101", "goalId": goal_id}, headers=headers)
    assert cv.status_code == 200 and cv.json()["cvText"]

    # Standard application (JOB-08)
    app_resp = client.post(
        "/v1/applications",
        json={"kind": "standard", "goalId": goal_id, "jobId": "j_102"},
        headers=headers,
    )
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    # ALREADY_APPLIED
    dup = client.post(
        "/v1/applications",
        json={"kind": "standard", "goalId": goal_id, "jobId": "j_102"},
        headers=headers,
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "ALREADY_APPLIED"

    # NOT_EXCLUSIVE_JOB (partner on non-exclusive job)
    bad_partner = client.post(
        "/v1/applications",
        json={"kind": "partner", "goalId": goal_id, "jobId": "j_103"},
        headers=headers,
    )
    assert bad_partner.status_code == 422 and bad_partner.json()["error"]["code"] == "NOT_EXCLUSIVE_JOB"

    # Manual status update (APP-06)
    upd = client.patch(f"/v1/applications/{app_id}", json={"manualStatus": "interview"}, headers=headers)
    assert upd.status_code == 200 and upd.json()["manualStatus"] == "interview"

    listing = client.get("/v1/applications", headers=headers)
    assert listing.json()["summary"]["total"] == 1


# --- AI Coaching (§9) ---
def test_coaching_review_and_mock(client):
    headers = auth_headers(client)
    goal_id = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers).json()["id"]
    app_id = client.post(
        "/v1/applications",
        json={"kind": "standard", "goalId": goal_id, "jobId": "j_102"},
        headers=headers,
    ).json()["id"]

    # AC-06: wrong file type
    bad = client.post(
        f"/v1/applications/{app_id}/interview-reviews",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "UNSUPPORTED_AUDIO_FORMAT"

    # AC-05: valid audio -> async analysis
    ok = client.post(
        f"/v1/applications/{app_id}/interview-reviews",
        files={"file": ("interview.mp3", b"fakeaudio", "audio/mpeg")},
        headers=headers,
    )
    assert ok.status_code == 202
    review_id = ok.json()["id"]
    for _ in range(4):
        r = client.get(f"/v1/applications/{app_id}/interview-reviews/{review_id}", headers=headers)
    assert r.json()["status"] == "complete"
    assert r.json()["review"]["dimensions"]

    archived = client.get(f"/v1/applications/{app_id}/interview-reviews", headers=headers)
    assert len(archived.json()) == 1

    # Mock interview (AC-11/12/14)
    start = client.post(f"/v1/applications/{app_id}/mock-interviews", headers=headers)
    assert start.status_code == 201
    session_id = start.json()["sessionId"]
    total = start.json()["totalQuestions"]

    last = None
    for i in range(total):
        last = client.post(
            f"/v1/applications/{app_id}/mock-interviews/{session_id}/turns",
            json={"text": f"My answer {i}"},
            headers=headers,
        )
    assert last.json()["status"] == "complete"
    assert last.json()["session"]["dimensions"]

    summary = client.get("/v1/ai-coaching/summary", headers=headers)
    assert summary.json()["mockCount"] == 1


def test_mock_end_early_requires_answer(client):
    headers = auth_headers(client)
    goal_id = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers).json()["id"]
    app_id = client.post(
        "/v1/applications",
        json={"kind": "standard", "goalId": goal_id, "jobId": "j_102"},
        headers=headers,
    ).json()["id"]
    session_id = client.post(
        f"/v1/applications/{app_id}/mock-interviews", headers=headers
    ).json()["sessionId"]

    # End before answering -> MOCK_SESSION_INCOMPLETE
    early = client.post(
        f"/v1/applications/{app_id}/mock-interviews/{session_id}/turns",
        json={"end": True},
        headers=headers,
    )
    assert early.status_code == 422 and early.json()["error"]["code"] == "MOCK_SESSION_INCOMPLETE"


# --- Alumni + Meetings (§10) + Notifications (§11) ---
def test_alumni_meetings_and_notifications(client):
    headers = auth_headers(client)

    alumni = client.get("/v1/alumni", headers=headers)
    assert alumni.status_code == 200 and len(alumni.json()) >= 1

    # AD-04: short message rejected
    short = client.post(
        "/v1/meetings",
        json={"alumniId": "a1", "topic": "Career", "message": "hi"},
        headers=headers,
    )
    assert short.status_code == 400

    # AD-03: valid request creates a notification
    ok = client.post(
        "/v1/meetings",
        json={"alumniId": "a1", "topic": "Career", "message": "I would love to learn about your path."},
        headers=headers,
    )
    assert ok.status_code == 201
    meeting_id = ok.json()["id"]

    # MEETING_ALREADY_PENDING
    dup = client.post(
        "/v1/meetings",
        json={"alumniId": "a1", "topic": "Career", "message": "Another request that is long enough."},
        headers=headers,
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "MEETING_ALREADY_PENDING"

    notifs = client.get("/v1/notifications", headers=headers)
    assert notifs.json()["total"] >= 1

    # AL-08: mark completed
    done = client.patch(f"/v1/meetings/{meeting_id}", json={"status": "completed"}, headers=headers)
    assert done.status_code == 200 and done.json()["status"] == "completed"

    # Mark all read (NT-03)
    read = client.post("/v1/notifications/read", json={}, headers=headers)
    assert all(n["read"] for n in read.json()["items"])
