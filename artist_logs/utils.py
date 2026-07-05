def split_composers(composer_string):
    """Split a comma-separated composer string into a list of individual composers"""
    if not composer_string:
        return []
    return [c.strip() for c in composer_string.split(',') if c.strip()]