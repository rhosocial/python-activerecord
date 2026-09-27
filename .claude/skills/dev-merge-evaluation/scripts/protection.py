# .claude/skills/dev-merge-evaluation/scripts/protection.py
"""Branch protection reality check: rulesets, legacy protection, and bypass actors.

Why this exists
---------------
The most expensive mistake in this area is concluding "this branch is
unprotected" from a 404. ``GET /repos/{owner}/{repo}/branches/{branch}/protection``
returns ``404 Branch not protected`` in two different situations:

1. the branch genuinely has no protection, and
2. the branch is protected through a **ruleset**, which that endpoint does not
   report at all.

A ruleset-based repository therefore looks unprotected through the legacy endpoint
while being strictly protected. Worse, ``gh api`` writes the API's JSON *error*
object to stdout for a 4xx, so a naive parse of that response yields a truthy dict
and reports an unprotected branch as protected. Both directions of this error
have been observed in this workspace.

This tool never infers protection from a single endpoint. It cross-checks
independent signals and, crucially, reports **who can bypass** the rules, because
a ruleset every admin bypasses at will has already been circumvented in practice
no matter how strict its rule list reads.

Signals
-------
``branches/{branch}.protected``
    Authoritative boolean, readable without admin permission. Primary signal.

``rulesets`` filtered to rules targeting this branch
    Where the rules actually live on a ruleset-based repository. Three condition
    shapes are handled: fully qualified names (``refs/heads/main``), globs
    (``refs/heads/release/v*``), and the special selectors ``~DEFAULT_BRANCH`` and
    ``~ALL``. Missing any of these silently under-reports protection.

``branches/{branch}/protection`` (legacy)
    Reported for completeness, explicitly labelled non-authoritative, and only
    when the request actually succeeded.

Usage
-----
    python protection.py --repo <owner/name> [--branch main] [--json]

Requires ``gh`` on PATH and an authenticated session. Exit code is 0 when the
branch is protected and 1 when it is not.
"""

import argparse
import fnmatch
import json
import subprocess
import sys

RULESET_RULE_DOC = {
    "deletion": "branch deletion blocked",
    "non_fast_forward": "force-push blocked",
    "update": "branch rename blocked",
    "creation": "branch creation restricted",
    "required_linear_history": "merge commits rejected",
    "required_signatures": "commits must be signed",
    "required_status_checks": "status checks must pass",
    "required_review_thread_resolution": "review threads must be resolved",
    "pull_request": "pull request required before merge",
    "code_quality": "code-quality findings block merge",
    "commit_author_email_pattern": "author email pattern enforced",
    "commit_message_pattern": "commit message pattern enforced",
    "branch_name_pattern": "branch name pattern enforced",
}

ACTOR_KIND = {
    "OrganizationAdmin": "org admin",
    "RepositoryRole": "repository role",
    "Integration": "integration/app",
    "Team": "team",
    "RepositoryAdmin": "repo admin (legacy protection)",
    "DeployKey": "deploy key",
}


def gh_json(args):
    """Run ``gh api`` and parse stdout, or return None.

    A non-zero exit always yields None even when stdout holds a parseable body:
    ``gh api`` writes the API's JSON error object to stdout on 4xx (the legacy
    protection endpoint returns ``{"message": "Branch not protected", ...}`` with
    exit status 1). Parsing that as a response is how an unprotected branch gets
    reported as protected, so exit status is authoritative and never ignored.
    """
    proc = subprocess.run(["gh", "api"] + list(args), capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    if not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return None


def summarise_rules(rules):
    summaries = []
    for rule in rules or []:
        kind = rule.get("type", "?")
        params = rule.get("parameters") or {}
        detail = RULESET_RULE_DOC.get(kind, "")
        if kind == "required_status_checks":
            names = [c.get("context", "?") for c in params.get("required_status_checks") or []]
            detail = "status checks: " + (", ".join(names) if names else "none listed")
            if params.get("strict_required_status_checks_policy"):
                detail += " (strict: branch must be up to date)"
        elif kind == "pull_request":
            count = params.get("required_approving_review_count")
            bits = ["approvals={}".format(count if count is not None else 0)]
            if params.get("require_code_owner_review"):
                bits.append("code-owner review")
            if params.get("dismiss_stale_reviews_on_push"):
                bits.append("dismiss stale reviews on push")
            methods = params.get("allowed_merge_methods") or []
            if methods:
                bits.append("merge methods=" + "/".join(methods))
            detail = "PR required, " + ", ".join(bits)
        elif kind == "code_quality":
            detail = "code quality: severity={}".format(params.get("severity", "?"))
        summaries.append((kind, detail or kind))
    return summaries


def ref_matches(branch, pattern, default_branch=None):
    """Whether a ruleset ``ref_name`` pattern covers *branch*."""
    if pattern == "~ALL":
        return True
    if pattern == "~DEFAULT_BRANCH":
        return bool(default_branch) and branch == default_branch
    full = "refs/heads/" + branch
    for candidate in (full, branch):
        if candidate == pattern:
            return True
        if any(ch in pattern for ch in "*?["):
            if fnmatch.fnmatch(candidate, pattern):
                return True
    return False


def rulesets_for_branch(owner_repo, branch, default_branch=None):
    matched = []
    for entry in gh_json(["repos/{}/rulesets".format(owner_repo)]) or []:
        if entry.get("target") != "branch":
            continue
        detail = gh_json(["repos/{}/rulesets/{}".format(owner_repo, entry["id"])])
        if not detail:
            continue
        ref_name = (detail.get("conditions") or {}).get("ref_name") or {}
        include = ref_name.get("include") or []
        exclude = ref_name.get("exclude") or []
        if not any(ref_matches(branch, p, default_branch) for p in include):
            continue
        if any(ref_matches(branch, p, default_branch) for p in exclude):
            continue
        matched.append(
            {
                "id": entry["id"],
                "name": entry.get("name"),
                "enforcement": entry.get("enforcement"),
                "rules": summarise_rules(detail.get("rules")),
                "bypass_actors": detail.get("bypass_actors") or [],
            }
        )
    return matched


def describe_actor(actor):
    kind = actor.get("actor_type", "?")
    label = ACTOR_KIND.get(kind, kind)
    mode = actor.get("bypass_mode", "?")
    actor_id = actor.get("actor_id")
    if kind == "OrganizationAdmin" and not actor_id:
        return "{} (bypass_mode={})".format(label, mode)
    return "{} id={} (bypass_mode={})".format(label, actor_id, mode)


def evaluate(owner_repo, branch):
    report = {
        "repo": owner_repo,
        "branch": branch,
        "default_branch": None,
        "protected_flag": None,
        "legacy_protection": None,
        "rulesets": [],
        "bypass_summary": [],
        "unprotected_reason": None,
    }

    repo_info = gh_json(["repos/{}".format(owner_repo)]) or {}
    report["default_branch"] = repo_info.get("default_branch")

    branch_info = gh_json(["repos/{}/branches/{}".format(owner_repo, branch)])
    if branch_info is None:
        report["unprotected_reason"] = "branch {!r} not found in {}".format(branch, owner_repo)
        return report
    report["protected_flag"] = bool(branch_info.get("protected"))

    legacy = gh_json(["repos/{}/branches/{}/protection".format(owner_repo, branch)])
    report["legacy_protection"] = bool(legacy) if legacy is not None else None

    report["rulesets"] = rulesets_for_branch(owner_repo, branch, report["default_branch"])
    for ruleset in report["rulesets"]:
        for actor in ruleset["bypass_actors"]:
            report["bypass_summary"].append((ruleset["name"], describe_actor(actor)))

    if not report["protected_flag"] and not report["rulesets"]:
        report["unprotected_reason"] = "protected=false and no ruleset targets this branch"
    return report


def render(report):
    lines = []
    add = lines.append
    add("Branch protection report")
    add("  repo:   {}".format(report["repo"]))
    add("  branch: {}".format(report["branch"]))
    if report.get("default_branch"):
        add("  default: {}".format(report["default_branch"]))
    add("")

    if report["unprotected_reason"]:
        add("  UNPROTECTED: {}".format(report["unprotected_reason"]))
        return "\n".join(lines)

    add("  branches/<branch>.protected  = {}".format(report["protected_flag"]))
    legacy = report["legacy_protection"]
    add("  legacy protection endpoint  = {}".format(
        "absent (404 or no legacy protection)" if legacy is None else legacy
    ))
    add("    (not authoritative: it also 404s when protection comes from a ruleset,")
    add("     which is why the two signals can legitimately disagree)")
    add("")

    if not report["rulesets"]:
        add("  no ruleset targets this branch")
    for ruleset in report["rulesets"]:
        add("  ruleset {} ({}) enforcement={}".format(
            ruleset["id"], ruleset["name"], ruleset["enforcement"]
        ))
        for kind, detail in ruleset["rules"] or [("(no rules)", "")]:
            add("      {:<26} {}".format(kind, detail))
        add("")

    if report["bypass_summary"]:
        add("  BYPASS ACTORS (a strict rule list means little if these exist):")
        for name, actor in report["bypass_summary"]:
            add("      [{}] {}".format(name, actor))
        add("")
        add("  Enforcement note: commits that landed while an always-bypass actor")
        add("  existed did not pass review, status checks, or signatures, even though")
        add("  the ruleset lists them as required. Check the PR list for those commits")
        add("  before treating the branch history as reviewed.")
    else:
        add("  no bypass actors: the rules cannot be skipped by any actor")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report real branch protection, including ruleset bypass actors."
    )
    parser.add_argument("--repo", required=True, help="owner/name of the repository")
    parser.add_argument("--branch", default="main", help="branch to inspect")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    if gh_json(["user"]) is None:
        print("error: 'gh api user' failed; run 'gh auth login' first", file=sys.stderr)
        return 2

    report = evaluate(args.repo, args.branch)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 1 if report["unprotected_reason"] else 0


if __name__ == "__main__":
    sys.exit(main())
