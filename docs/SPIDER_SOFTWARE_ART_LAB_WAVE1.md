# Spider Software: Art Lab native application, first working wave

## Why this exists
Spider Art Lab is **software**, not a shortcut to Dolphin, GIMP or a list of
Linux graphics packages. The existing `art-lab` tab in The Web now mounts
`art_lab/main.py:SpiderArtLab` directly using the same `create_native`
contract as Studio, Author and Study. It retains existing external creative
tools rather than uninstalling or replacing them.

### Working features in the source branch
- Purpose-built purple Qt painting surface with original Spider Art Lab
  icon (`branding/spider-apps/icons/spider-art-lab.svg`) and dedicated
  app/workspace background asset
  (`branding/spider-apps/backgrounds/spider-art-lab.svg`).
- New 1600 × 900 transparent editable canvas, pencil, brush, translucent
  marker, layer-scoped eraser, stroke width 1–128, color picker,
  antialiasing, cursor tracking and 25–200% zoom.
- Named 32-layer stack with hide/show, reordering, rename, delete confirmation
  and painting on the selected layer. A 25-step undo/redo snapshot history.
- Editable, validated, locally saved **.spiderart** source documents with
  bounded stroke-point and file sizes and version 1 schema. Open projects
  preserve editable strokes and embedded image references.
- Import PNG photos (max 8 MiB, dimensions max 4096 × 4096) as their own
  reference layer; **Photo → Outline** uses local bounded Sobel-style
  luminance detection and creates a separate transparent ink layer
  for tracing. No cloud API or generative image training.
- Export actual lossless transparent PNG pictures. **Save New Project** and
  **Export PNG** create new owner files, never silently overwrite older art.
  Files have private 0600 permissions.

### Test coverage
- `tests/test_spider_art_lab.py`: real editable document roundtrip, project
  format/coordinate limits, symlink and overwrite rejection, private file
  permissions, antialiased brush + layer erasure, actual saved PNG pixels,
  native canvas undo/redo and layer order, photo-edge rendering,
  photo-outline undo, and `create_native("art-lab")` integration.

### Spider Software lineup
The owner's named software roadmap is:
Spider Audio Studio; Spider Art Lab; Spider Video Studio; Spider 3D World;
Spider Author Pro; Spider Study Pro; Spider Media Center Pro;
Spider Connect; Spider Security Center; Spider Control Center;
Webbie Intelligence Center.

Art Lab is the first app beyond Audio Studio in this new source branch.
It is NOT a fabricated placeholder for the remaining products. The
existing installed Ubuntu Studio creative apps remain available inside
Spider OS. Each Spider software app retains an individual icon/background,
and productive controls belong INSIDE the appropriate native bay.

### Release status
GitHub branch `feature/spider-software-art-lab-20261016` is based on
Audio Studio's Wave 9 feature branch. Neither branch is yet merged into
the owner's known-good installed PC system. Prior audits reported
unknown owner-customized installed paths requiring explicit reconciliation.
A passing CI test is not evidence the art application has been installed
or tablet pen hardware supports pressure sensitivity. Hardware pressure,
selection masks, layered blending modes, vector paths and advanced
print-color management are not implemented here.

Do not overwrite any installed Art Lab, Studio, Webbie, other native bay,
music, radio or existing artwork during source staging.
