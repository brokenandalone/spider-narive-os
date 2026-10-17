"""Default workspace address forms for Webbie.

Owner preferences take precedence. Defaults are not proof of identity or voice
authorization. Use only as friendly forms of address after authorization.
"""
DEFAULT_NAMES = {'author': 'Writer', 'study': 'Student', 'school': 'Student',
                 'studio': 'Justin', 'kali-bay': 'Spider'}


def context_name(workspace, config=None):
    if not isinstance(config, dict):
        config = {}
    mapping = config.get('context_names')
    if not isinstance(mapping, dict):
        mapping = {}
    chosen = mapping.get(workspace)
    if isinstance(chosen, str) and chosen.strip():
        return chosen.strip()
    if workspace in DEFAULT_NAMES:
        return DEFAULT_NAMES[workspace]
    name = config.get('default_user_name')
    return name.strip() if isinstance(name, str) and name.strip() else 'Cory'
