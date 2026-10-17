# Spider OS Mission Control: Home focus queue

The existing native Home Dashboard has a six-item **Mission Control** queue,
not a separate application. It reads only the private existing MissionStore
entries. Blocked missions show first, followed by active and next. Selecting
a row navigates to its native bay through the existing workspace opener.
It does not open linked documents, use the network, execute a mission or
authorize Webbie to control the computer.

This implements the owner's unified 'one OS' workflow without replacing
existing tools, breaking the project handoff model, or activating services.

## Verification
Pure queue ordering, bounded display, invalid data, and UI integration have
source tests. Deployment is still **BLOCKED** by owner-specific native Desktop
and Webbie merge reviews, backups, and local Qt tests. Source work on this
draft GitHub branch is not an installation.
