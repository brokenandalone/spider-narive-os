"""Optional, owner-controlled familiar face profiles for the Spider OS webcam.

Enrollment uses an optional local face-embedding package. The only saved data
are face descriptors for two explicitly enrolled adults, never camera images.
This is a convenience cue, NOT speaker authentication or security access.
"""
import io
import json
import math
import os
from pathlib import Path
import stat

PROFILES = ('Cory', 'Shayna')
MAX_SAMPLES = 5
MATCH_THRESHOLD = 0.43
MARGIN_THRESHOLD = 0.075


def _face_backend():
    try:
        import face_recognition
        return face_recognition
    except ImportError:
        raise RuntimeError(
            'Optional local face matching is not installed. Room vision and '
            'Webbie’s existing microphone still work without face profiles.'
        ) from None


def encode_face(jpeg):
    if not isinstance(jpeg, bytes) or len(jpeg) > 4 * 1024 * 1024:
        raise ValueError('Invalid camera image.')
    recognizer = _face_backend()
    image = recognizer.load_image_file(io.BytesIO(jpeg))
    locations = recognizer.face_locations(image, model='hog')
    if len(locations) != 1:
        raise ValueError('Enrollment needs exactly one clearly visible face in the picture.')
    matches = recognizer.face_encodings(image, known_face_locations=locations)
    if len(matches) != 1:
        raise RuntimeError('Face features could not be extracted; adjust the lighting and try again.')
    descriptor = [float(number) for number in matches[0]]
    if len(descriptor) != 128 or not all(math.isfinite(number) for number in descriptor):
        raise ValueError('The face description was incomplete.')
    return descriptor


class FaceProfiles:
    """Opt-in local similarity, not an identity guarantee or authority grant."""

    def __init__(self, path=None):
        root = Path(os.environ.get(
            'XDG_DATA_HOME', str(Path.home() / '.local/share')
        )) / 'spider-os'
        self.path = Path(path) if path is not None else root / 'webbie-face-profiles.json'
        self.samples = {name: [] for name in PROFILES}
        self.load_error = None
        try:
            self.load()
        except (OSError, ValueError, TypeError, KeyError) as error:
            # An absent, unreadable or malformed optional face database must
            # never block Webbie's ordinary vision or microphone.
            self.samples = {name: [] for name in PROFILES}
            self.load_error = 'Face profiles unavailable. No profiles are required.'

    def load(self):
        try:
            if self.path.is_symlink():
                raise ValueError('Refusing a symbolic link for face profiles.')
            if self.path.stat().st_size > 350000:
                raise ValueError('Face profile data file is unexpectedly large.')
            payload = json.loads(self.path.read_text('utf-8'))
            if payload.get('schema') != 1:
                raise ValueError('Unsupported face profile file.')
            for name in PROFILES:
                vectors = payload.get('profiles', {}).get(name, [])
                if not isinstance(vectors, list) or len(vectors) > MAX_SAMPLES:
                    raise ValueError('Invalid face profile sample count.')
                clean = []
                for vector in vectors:
                    if not isinstance(vector, list) or len(vector) != 128:
                        raise ValueError('Invalid face profile vector.')
                    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector):
                        raise ValueError('Invalid face profile data.')
                    clean.append([float(v) for v in vector])
                self.samples[name] = clean
        except FileNotFoundError:
            return

    def status(self):
        return {name: len(self.samples[name]) for name in PROFILES}

    def any_enrolled(self):
        return any(self.samples[name] for name in PROFILES)

    def write(self):
        if self.path.is_symlink():
            raise ValueError('Refusing to overwrite a profile symlink.')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.parent.is_symlink():
            raise ValueError('Refusing to store profiles in a symbolic-link directory.')
        os.chmod(self.path.parent, 0o700)
        tmp = self.path.with_name(self.path.name + '.tmp')
        if tmp.exists() or tmp.is_symlink():
            raise ValueError('A pending face profile write already exists.')
        descriptor = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
                json.dump({'schema': 1, 'profiles': self.samples}, output)
                output.write('\n')
            tmp.replace(self.path)
            os.chmod(self.path, 0o600)
        finally:
            tmp.unlink(missing_ok=True)

    def enroll_descriptor(self, name, descriptor):
        if name not in PROFILES:
            raise ValueError('Face enrollment is limited to the two opted-in profiles.')
        if len(descriptor) != 128 or not all(
            isinstance(v, (float, int)) and math.isfinite(v) for v in descriptor
        ):
            raise ValueError('Invalid enrolled face descriptor.')
        if len(self.samples[name]) >= MAX_SAMPLES:
            raise ValueError('Maximum enrollment samples reached; reset the profile to begin again.')
        self.samples[name].append([float(v) for v in descriptor])
        try:
            self.write()
        except Exception:
            self.samples[name].pop()
            raise

    def forget(self, name):
        if name not in PROFILES:
            raise ValueError('Unknown face profile.')
        prior = self.samples[name]
        self.samples[name] = []
        try:
            self.write()
        except Exception:
            self.samples[name] = prior
            raise

    def match_descriptor(self, descriptor):
        if not self.any_enrolled():
            return None
        if not isinstance(descriptor, (tuple, list)) or len(descriptor) != 128:
            return None
        scored = []
        for name in PROFILES:
            for saved in self.samples[name]:
                distance = math.sqrt(sum((float(a) - b) ** 2 for a, b in zip(descriptor, saved)))
                scored.append((distance, name))
        if not scored:
            return None
        top = {}
        for distance, name in scored:
            top[name] = min(distance, top.get(name, 999))
        ordered = sorted((distance, name) for name, distance in top.items())
        if ordered[0][0] > MATCH_THRESHOLD:
            return None
        if len(ordered) > 1 and ordered[1][0] - ordered[0][0] < MARGIN_THRESHOLD:
            return None
        return ordered[0][1]


def find_enrolled_faces(jpeg, profiles):
    if not profiles.any_enrolled():
        return []
    recognizer = _face_backend()
    image = recognizer.load_image_file(io.BytesIO(jpeg))
    locations = recognizer.face_locations(image, model='hog')
    names = []
    for descriptor in recognizer.face_encodings(image, known_face_locations=locations):
        result = profiles.match_descriptor(descriptor)
        if result is not None and result not in names:
            names.append(result)
    return names
