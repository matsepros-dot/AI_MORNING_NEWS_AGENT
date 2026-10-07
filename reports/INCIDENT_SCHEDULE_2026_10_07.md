# Scheduled workflow incident — 2026-10-07

Result: FAIL for on-time automatic updates. Root cause unconfirmed.
Checked at: 2026-10-07T10:06:34.772170+07:00 (Vietnam UTC+07:00).

## Verified evidence

- Repository: https://github.com/matsepros-dot/AI_MORNING_NEWS_AGENT
- Workflow: .github/workflows/morning-news.yml on default branch main; remote content matches local.
- Public repository, not a fork, not archived/disabled; Actions enabled; workflow active.
- Last cron commits map to GitHub account matsepros-dot, which exists as a User.
- Repository-wide API query event=schedule returns total_count=0 (also zero for specific workflow).
- Current cron UTC: 0 1 * * *; 30 6 * * *; 0 2-10 7 10 *; 30 1-5,7-10 7 10 *.
- Expected trial slots 09:00, 09:30, 10:00 Vietnam; policy simulation permits each.
- No schedule run exists, so runner setup, date/window policy, source fetching, and publishing were not reached by these scheduled triggers.
- Last successful manual run: https://github.com/matsepros-dot/AI_MORNING_NEWS_AGENT/actions/runs/37559037115
- Public news timestamp remains 2026-10-07T08:50:54.124111+07:00.
- Pages built latest code commit 3f8bf6c8c7f90953b68928c7ca3c7a31b4293f1d.
- Live GitHub status API reports Actions and Pages operational. This does not rule out a repository-specific issue.

## Limits of diagnosis

The observed failure is before workflow creation. Repository API does not expose internal cron registration/dispatch logs. Delay/drop is documented by GitHub but has NOT been proven as the root cause of this incident. Passing pipeline/unit tests does not establish scheduler reliability.
No supplemental triggers, manual runs, retries, or undocumented scheduler resets were performed during this investigation.

## Draft for GitHub Support (not sent)

Our public repository has an active scheduled workflow on its default branch main. Manual runs succeeded earlier, but no schedule event has ever appeared in repository-wide Actions runs. On October 7, 2026, scheduled slots at 01:00, 02:00 and 02:30 UTC produced no visible run by the check above. Please inspect internal schedule registration and event dispatch for this repository/workflow. Actions are enabled, the repository is not a fork or archived, and the cron author account is accessible through the GitHub user API. Current workflow URL: https://github.com/matsepros-dot/AI_MORNING_NEWS_AGENT/blob/main/.github/workflows/morning-news.yml

Root-cause confirmation requires GitHub-side diagnostics. Changing pipeline code cannot repair a trigger that GitHub has not emitted.
