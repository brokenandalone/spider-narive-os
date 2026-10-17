"""Editable starting-point mix recipes, not automatic mixing or mastering."""
if __package__:
    from .band_mix import ROLES
else:
    from band_mix import ROLES

PRESETS = {
    'neutral': {
        'name': 'Neutral | all tracks centered',
        'gains': {},
        'pans': {},
    },
    'broken_sorrow': {
        'name': 'Broken Sorrow | heavy two-guitar spread',
        'gains': {
            'backing': .75, 'lead_vocal': 1.10, 'guest_vocal': .86,
            'rhythm_guitar': .95, 'lead_guitar': .88,
            'bass': 1.0, 'drums': 1.0, 'keys': .55,
        },
        'pans': {
            'rhythm_guitar': -.65, 'lead_guitar': .50,
            'guest_vocal': .16, 'keys': -.18,
        },
    },
    'duet': {
        'name': 'Vocal duet | two singers out front',
        'gains': {
            'backing': .75, 'lead_vocal': 1.04, 'guest_vocal': 1.04,
            'rhythm_guitar': .77, 'lead_guitar': .72,
            'bass': .83, 'drums': .84, 'keys': .70,
        },
        'pans': {
            'lead_vocal': -.18, 'guest_vocal': .18,
            'rhythm_guitar': -.43, 'lead_guitar': .43,
        },
    },
    'piano': {
        'name': 'Haunted piano | sparse, intimate',
        'gains': {
            'backing': .58, 'lead_vocal': 1.08, 'guest_vocal': .55,
            'rhythm_guitar': .38, 'lead_guitar': .40,
            'bass': .65, 'drums': .48, 'keys': 1.05,
        },
        'pans': {
            'rhythm_guitar': -.3, 'lead_guitar': .3, 'keys': .15,
        },
    },
}
PRESET_IDS = tuple(PRESETS)


def preset_mix_values(preset_id, roles=ROLES):
    """Return bounded independent gain/pan mapping for a known recipe."""
    if preset_id not in PRESETS:
        raise ValueError('Unknown Studio mix preset.')
    if any(role not in ROLES for role in roles):
        raise ValueError('Unknown band role in preset application.')
    choice = PRESETS[preset_id]
    return (
        {role: choice['gains'].get(role, 1.0) for role in roles},
        {role: choice['pans'].get(role, 0.0) for role in roles},
    )
