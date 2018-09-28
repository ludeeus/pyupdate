"""Logic to handle common functions."""


def get_default_repos():
    """Return default repos."""
    git_base = 'https://raw.githubusercontent.com/'
    cards = git_base + 'custom-cards/information/master/repos.json'
    components = git_base + 'custom-components/information/master/repos.json'
    return [cards, components]
