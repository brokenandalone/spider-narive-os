# Study Major Upgrade: Assignment Steps, Research Sources, Weekly Plan

## Baseline and release status

The owner confirmed a **full installation of the October 10, 2026 upgrades** on their actual Spider OS PC. Protect that as the currently installed state. These October 11 source changes are **not installed merely because GitHub tests pass**. This pull request is stacked on PR #64, which builds on Study Planner PR #53 and Studio/School PR #34.

## New features

**Assignment milestone checklists:** each existing assignment has its own user-managed task checklist, optional personal target dates, completion progress, and an explicitly confirmed starter checklist. Duplicate starter steps are not imported twice. All steps are private and confined to their assignment. Deleting an assignment removes its checklist after an explicit warning; it never removes saved course folder documents.

**Manual source notebook:** store a complete reference as you entered it, an optional URL/DOI/ISBN or library locator, and research notes. Nothing is automatically scraped or verified. Sources never silently become citations. The Use in References button requires explicit confirmation and appends an exact, nonduplicate copy of the selected reference to the assignment's editable References field. The APA Word document export continues to use user-entered references, which must be verified before submission.

**Weekly workload board:** a single view of the locally tracked courses showing assignments due in 7, 14 or 30 days, all overdue assignments, and undated assignments. Each entry includes per-assignment steps completed and the first unfinished step. Double-clicking opens that exact assignment's notebook. Dates are not guessed, and items outside the selected window are hidden unless overdue or undated. Completed assignments are hidden by default with an explicit toggle to show them.

**Deletion safety:** confirms when an assignment contains any saved notebook text, steps, or source references, and explains which local records will be deleted. Course files in Documents are not deleted.

## Technical changes

- Additive SQLite tables: assignment_steps and assignment_sources; no changes to existing columns, credentials, user data roots, or already installed service names.
- Local source validation for dates, step names, references and notes; all entry points require user actions.
- Shared reversible batch release includes four modules: study/milestones.py, study/milestones_ui.py, study/source_library_ui.py, study/weekly_planner_ui.py.
- Desktop installer preflights all four modules, adds missing modules only and preserves unknown installed source edits with existing reconciliation gates.
- No school account login, assignment submission, unsolicited cloud transfer or alleged source verification.

## Installation gates

1. Check GitHub source tests and native Qt smoke tests for the exact commit.
2. Verify installed PC versions and preserve October 10 local modifications. Stop on unrecognized Study or Webbie code.
3. Back up the local Study database and Documents/Spider OS/Study course directory before installing.
4. Open an existing assignment, add steps, mark one complete, save a source, and explicitly append it to References.
5. Open Weekly Plan, verify 7/14/30 day filters and undated entries, and open the right course/assignment by double-click.
6. Restart Study. Confirm all existing course notes, earlier saved drafts and user-entered scores are intact.
7. Check APA export and confirm it has only approved user-entered references. Verify every citation independently.
8. The owner PC must confirm installed SNHU and OneDrive authentication separately. GitHub cannot establish those.
