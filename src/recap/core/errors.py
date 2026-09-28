class RecapError(Exception):
    """An expected, user-actionable failure."""


class ExternalCommandError(RecapError):
    """A local command failed or exceeded its time limit."""
