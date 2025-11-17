"""
Custom exceptions for the application
"""

from fastapi import HTTPException


class NotFoundError(HTTPException):
    """Resource not found"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedError(HTTPException):
    """Unauthorized access"""
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(HTTPException):
    """Forbidden access"""
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=403, detail=detail)


class ValidationError(HTTPException):
    """Validation error"""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=400, detail=detail)

