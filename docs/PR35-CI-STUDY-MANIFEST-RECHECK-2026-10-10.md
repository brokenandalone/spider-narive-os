# PR #35 Studio and Study integration regression rerun

The October 10 pull-request workflow initially reported a failure in the
Study batch manifest test, while its same-head push check passed. The
failed PR merge preview checked that `Item.reference` values were unique.
That assumption is wrong: the floating-face autostart source is intentionally
installed to two distinct destination paths. The release installer must
validate **unique target paths**, not falsely reject a legitimate shared
source reference.

The current upstream Studio/Study base test now asserts that
`prepare_items()` returns unique `Item.target` paths and checks all
sources exist. This is the correct safety property. The production release
code also asserts unique destinations. Do not remove that guard.

This note is a traceable no-runtime-change update to revalidate PR #35
against the latest base with GitHub Actions, rather than claiming the
oldest failed check was successful. Device installation is still blocked
pending the separate cross-branch/installed-PC reconciliation (draft PR #48).
