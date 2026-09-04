""" Import order matters for SQLAlchemy relationships
 Tenant has no direct runtime imports
 Widget depends on Tenant
 Submission depends on both Tenant and Widget"""
from src.module.schemas.tenant import Tenant
from src.module.schemas.widget import Widget
from src.module.schemas.submission import Submission

# Ensure all models are registered with SQLAlchemy's mapper
__all__ = ["Tenant", "Widget", "Submission"]
