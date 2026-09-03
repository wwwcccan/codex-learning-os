class LearningOSError(Exception):
    """Base error for expected user-facing failures."""


class ValidationError(LearningOSError, ValueError):
    """Raised when a Markdown record violates its versioned schema."""


class RecordNotFoundError(LearningOSError, FileNotFoundError):
    """Raised when a requested vault record does not exist."""


class DuplicateRecordError(LearningOSError):
    """Raised when creating a record would overwrite a different record."""
