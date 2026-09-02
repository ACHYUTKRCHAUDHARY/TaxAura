from enum import StrEnum


class DocumentStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaxRegime(StrEnum):
    OLD = "OLD"
    NEW = "NEW"


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
