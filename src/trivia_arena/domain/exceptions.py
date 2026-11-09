class DomainError(Exception):
    """Base for mapped HTTP domain failures."""


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ValidationDomainError(DomainError):
    pass
