"""
Custom exceptions for the backend application.
"""
from typing import Optional


class BackendError(Exception):
    """Base exception for all backend errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class ValidationError(BackendError):
    """Raised when input validation fails."""
    pass


class NotFoundError(BackendError):
    """Raised when a requested resource is not found."""
    pass


class DatabaseError(BackendError):
    """Raised when a database operation fails."""
    pass


class ServiceError(BackendError):
    """Base exception for service-related errors."""
    pass


class AlphaFoldError(ServiceError):
    """Raised when AlphaFold prediction fails."""
    pass


class DockingError(ServiceError):
    """Raised when molecular docking fails."""
    pass


class AIReportError(ServiceError):
    """Raised when AI report generation fails."""
    pass


class BlockchainError(ServiceError):
    """Raised when blockchain operations fail."""
    pass


class FileProcessingError(BackendError):
    """Raised when file processing fails."""
    pass
