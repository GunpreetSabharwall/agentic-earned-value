"""Acceptance, clawback and authorship rules."""

from datetime import datetime, timezone

from aev.items import (
    authorship_class,
    build_episodes,
    build_work_items,
    parse_time,
    points_from_labels,
)

AS_OF = datetime(2026, 3, 1, tzinfo=timezone.utc)


def t(day, hour=12):
    return datetime(2026, 1, day, hour, tzinfo=timezone.utc)


def closed(day, reason="completed"):
    return {"type": "closed", "at": t(day).isoformat(), "reason": reason}


def reopened(day):
    return {"type": "reopened", "at": t(day).isoformat()}


# --- points labels ------------------------------------------------------------------

def test_points_label_parsed():
    assert points_from_labels(["bug", "aev-points:5"]) == (5.0, None)


def test_points_label_tolerates_case_and_spaces():
    assert points_from_labels(["AEV-Points: 3"])[0] == 3.0


def test_points_label_decimal():
    assert points_from_labels(["aev-points:0.5"])[0] == 0.5


def test_no_points_label():
    assert points_from_labels(["bug"]) == (None, None)


def test_several_points_labels_uses_largest_and_warns():
    points, warning = points_from_labels(["aev-points:2", "aev-points:8"])
    assert points == 8.0
    assert "several" in warning


# --- authorship class -----------------------------------------------------------------

def test_class_agent_when_all_prs_by_agents():
    assert authorship_class(["bot-a", "bot-b"], ["bot-a", "bot-b"]) == "A"


def test_class_human_when_no_pr_by_agent():
    assert authorship_class(["person"], ["bot-a"]) == "H"


def test_class_mixed():
    assert authorship_class(["bot-a", "person"], ["bot-a"]) == "M"


def test_class_none_without_merged_prs():
    assert authorship_class([], ["bot-a"]) is None


def test_class_ignores_bot_suffix_and_case():
    assert authorship_class(["My-Agent[bot]"], ["my-agent"]) == "A"
    assert authorship_class(["my-agent"], ["My-Agent[bot]"]) == "A"


def test_class_deleted_author_counts_as_human():
    assert authorship_class([None], ["bot-a"]) == "H"


# --- accept-then-hold ------------------------------------------------------------------

def test_accepted_when_closed_completed_with_merged_pr():
    eps = build_episodes([closed(10)], [t(10, 11)], [], 14, AS_OF)
    assert len(eps) == 1 and not eps[0].clawed_back
    assert eps[0].accepted_at == t(10)


def test_not_accepted_without_merged_pr():
    assert build_episodes([closed(10)], [], [], 14, AS_OF) == []


def test_not_accepted_when_closed_not_planned():
    assert build_episodes([closed(10, "not_planned")], [t(9)], [], 14, AS_OF) == []


def test_old_close_without_reason_counts_as_completed():
    assert len(build_episodes([closed(10, None)], [t(9)], [], 14, AS_OF)) == 1


def test_acceptance_time_is_later_of_close_and_merge():
    eps = build_episodes([closed(10)], [t(12)], [], 14, AS_OF)
    assert eps[0].accepted_at == t(12)


def test_reopen_within_window_claws_back():
    eps = build_episodes([closed(1), reopened(10)], [t(1)], [], 14, AS_OF)
    assert eps[0].clawed_back and eps[0].clawback_reason == "reopened"


def test_reopen_exactly_at_window_end_claws_back():
    eps = build_episodes([closed(1), reopened(15)], [t(1)], [], 14, AS_OF)
    assert eps[0].clawed_back


def test_reopen_after_window_keeps_value():
    eps = build_episodes([closed(1), reopened(20)], [t(1)], [], 14, AS_OF)
    assert len(eps) == 1 and not eps[0].clawed_back


def test_revert_within_window_claws_back():
    eps = build_episodes([closed(1)], [t(1)], [(t(5), "PR #9 reverted")], 14, AS_OF)
    assert eps[0].clawed_back and eps[0].clawback_reason == "PR #9 reverted"


def test_revert_after_window_keeps_value():
    eps = build_episodes([closed(1)], [t(1)], [(t(25), "PR #9 reverted")], 14, AS_OF)
    assert not eps[0].clawed_back


def test_clawed_back_item_can_earn_again_when_accepted_again():
    eps = build_episodes([closed(1), reopened(3), closed(6)], [t(1)], [], 14, AS_OF)
    assert [e.clawed_back for e in eps] == [True, False]


def test_close_after_late_reopen_does_not_earn_twice():
    eps = build_episodes([closed(1), reopened(20), closed(22)], [t(1)], [], 14, AS_OF)
    assert len(eps) == 1


def test_events_after_as_of_are_ignored():
    as_of = t(5)
    assert build_episodes([closed(10)], [t(1)], [], 14, as_of) == []
    eps = build_episodes([closed(1), reopened(10)], [t(1)], [], 14, as_of)
    assert not eps[0].clawed_back


def test_zero_day_window():
    eps = build_episodes([closed(1), reopened(2)], [t(1)], [], 0, AS_OF)
    assert not eps[0].clawed_back


# --- whole items -------------------------------------------------------------------------

def issue(number, labels, events, prs):
    return {"number": number, "title": f"Issue {number}", "labels": labels,
            "events": events, "linked_prs": prs}


def pr(number, author, day, reverted_day=None):
    return {"number": number, "author": author, "merged_at": t(day).isoformat(),
            "reverted_at": t(reverted_day).isoformat() if reverted_day else None}


def test_build_work_items_values_and_classes():
    snapshot = [
        issue(1, ["aev-points:5"], [closed(2)], [pr(10, "bot", 2)]),
        issue(2, ["aev-points:3"], [closed(2)], [pr(11, "person", 2, reverted_day=4)]),
        issue(3, ["aev-points:2"], [], []),
        issue(4, [], [closed(2)], [pr(12, "bot", 2), pr(13, "person", 2)]),
    ]
    items, warnings = build_work_items(snapshot, 1000, ["bot"], 14, AS_OF)
    by_number = {i.number: i for i in items}

    assert by_number[1].value == 5000 and by_number[1].ev == 5000
    assert by_number[1].authorship == "A"

    assert by_number[2].gross_ev == 3000 and by_number[2].clawback == 3000
    assert by_number[2].ev == 0 and by_number[2].authorship == "H"

    assert by_number[3].ev == 0 and by_number[3].authorship is None

    # No points label: no value, but class is still known (for costs).
    assert by_number[4].value == 0 and by_number[4].authorship == "M"
    assert warnings == []


def test_pr_merged_after_as_of_is_ignored():
    snapshot = [issue(1, ["aev-points:1"], [closed(2)], [pr(10, "bot", 2)])]
    items, _ = build_work_items(snapshot, 1000, ["bot"], 14, t(1))
    assert items[0].authorship is None and items[0].ev == 0


def test_parse_time_accepts_z_suffix_and_plain_dates():
    assert parse_time("2026-01-02T03:04:05Z") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert parse_time("2026-01-02").tzinfo is not None
    assert parse_time(None) is None


# --- v0.3.0: authorship of a single PR ------------------------------------------------

from aev.items import combine_classes, pr_class  # noqa: E402

AGENTS = ["claude", "my-agent[bot]", "agent@example.com"]


def commit(*authors):
    return {"authors": list(authors)}


def user(login):
    return {"login": login, "name": login.title(), "email": f"{login}@users.noreply.example"}


def no_user(name=None, email=None):
    return {"login": None, "name": name, "email": email}


def test_rule1_agent_label_makes_pr_agent():
    pr = {"author": "jane", "labels": ["aev-agent"], "commits": [commit(user("jane"))]}
    assert pr_class(pr, AGENTS) == "A"


def test_rule1_agent_label_is_case_insensitive():
    assert pr_class({"author": "jane", "labels": ["AEV-Agent"]}, AGENTS) == "A"


def test_rule1_custom_agent_label():
    pr = {"author": "jane", "labels": ["ai-made"]}
    assert pr_class(pr, AGENTS, agent_label="ai-made") == "A"
    assert pr_class(pr, AGENTS) == "H"  # default label not present
    assert pr_class({"author": "jane", "labels": ["aev-agent"]}, AGENTS, agent_label="ai-made") == "H"


def test_rule2_pr_author_in_agent_accounts():
    pr = {"author": "Claude", "commits": [commit(user("jane"))]}
    assert pr_class(pr, AGENTS) == "A"


def test_rule2_pr_author_with_or_without_bot_suffix():
    assert pr_class({"author": "my-agent"}, AGENTS) == "A"
    assert pr_class({"author": "claude[bot]"}, AGENTS) == "A"


def test_rule3_every_commit_has_agent_author():
    pr = {"author": "jane", "commits": [commit(user("claude")), commit(user("Claude[bot]"))]}
    assert pr_class(pr, AGENTS) == "A"


def test_rule3_agent_as_co_author_counts():
    pr = {"author": "jane", "commits": [commit(user("jane"), user("claude"))]}
    assert pr_class(pr, AGENTS) == "A"


def test_rule3_some_commits_agent_is_mixed():
    pr = {"author": "jane", "commits": [commit(user("claude")), commit(user("jane"))]}
    assert pr_class(pr, AGENTS) == "M"


def test_rule3_no_agent_commits_is_human():
    pr = {"author": "jane", "commits": [commit(user("jane")), commit(user("bob"))]}
    assert pr_class(pr, AGENTS) == "H"


def test_rule3_no_commit_information_is_human():
    assert pr_class({"author": "jane"}, AGENTS) == "H"
    assert pr_class({"author": "jane", "commits": []}, AGENTS) == "H"
    assert pr_class({"author": "jane", "commits": [commit()]}, AGENTS) == "H"


def test_commit_without_github_user_matches_exact_email_or_name():
    assert pr_class({"author": "jane", "commits": [commit(no_user(email="agent@example.com"))]}, AGENTS) == "A"
    assert pr_class({"author": "jane", "commits": [commit(no_user(name="claude"))]}, AGENTS) == "A"


def test_commit_without_github_user_needs_exact_match():
    for author in (no_user(email="AGENT@example.com"), no_user(name="Claude"),
                   no_user(name="claude-helper"), no_user()):
        assert pr_class({"author": "jane", "commits": [commit(author)]}, AGENTS) == "H", author


def test_commit_with_github_user_is_matched_by_login_not_email():
    author = {"login": "jane", "name": "claude", "email": "agent@example.com"}
    assert pr_class({"author": "jane", "commits": [commit(author)]}, AGENTS) == "H"


def test_no_agent_accounts_means_human_unless_labelled():
    pr = {"author": "claude", "commits": [commit(user("claude"))]}
    assert pr_class(pr, []) == "H"
    assert pr_class(dict(pr, labels=["aev-agent"]), []) == "A"


# --- v0.3.0: issue class from its PRs -----------------------------------------------------

def test_combine_classes():
    assert combine_classes([]) is None
    assert combine_classes(["A", "A"]) == "A"
    assert combine_classes(["H"]) == "H"
    assert combine_classes(["A", "H"]) == "M"
    assert combine_classes(["M"]) == "M"  # a mixed PR makes the issue mixed
    assert combine_classes(["A", "M"]) == "M"


def test_build_work_items_uses_commit_authors():
    # Agent opens the PR under the human's account; commits are by "claude".
    agent_pr = dict(pr(10, "jane", 2), commits=[commit(user("claude"))])
    mixed_pr = dict(pr(11, "jane", 2), commits=[commit(user("claude")), commit(user("jane"))])
    labelled = dict(pr(12, "jane", 2), labels=["aev-agent"])
    snapshot = [
        issue(1, ["aev-points:1"], [closed(2)], [agent_pr]),
        issue(2, ["aev-points:1"], [closed(2)], [mixed_pr]),
        issue(3, ["aev-points:1"], [closed(2)], [labelled]),
        issue(4, ["aev-points:1"], [closed(2)], [agent_pr, pr(13, "jane", 2)]),
    ]
    items, _ = build_work_items(snapshot, 1000, ["claude"], 14, AS_OF)
    assert [i.authorship for i in items] == ["A", "M", "A", "M"]


def test_build_work_items_custom_agent_label():
    labelled = dict(pr(12, "jane", 2), labels=["ai-made"])
    snapshot = [issue(1, ["aev-points:1"], [closed(2)], [labelled])]
    items, _ = build_work_items(snapshot, 1000, [], 14, AS_OF, agent_label="ai-made")
    assert items[0].authorship == "A"


def test_build_work_items_warns_when_commits_truncated():
    big = dict(pr(10, "jane", 2), commits=[commit(user("claude"))], commits_truncated=True)
    snapshot = [issue(1, ["aev-points:1"], [closed(2)], [big])]
    _, warnings = build_work_items(snapshot, 1000, ["claude"], 14, AS_OF)
    assert any("PR #10" in w and "100 commits" in w for w in warnings)
