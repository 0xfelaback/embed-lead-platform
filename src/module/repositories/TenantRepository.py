import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from src.main import logger
from src.module.schemas import Tenant


class TenantRepository:
    """
    Repository for Tenant entity with multi-tenancy support.

    This repository provides CRUD operations for tenants while ensuring
    proper data isolation and following multi-tenancy architecture patterns.
    Since Tenant is the top-level entity in the hierarchy, operations here
    affect the entire tenant scope including all related widgets and submissions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, email: str, key_hash: str) -> Optional[Tenant]:
        """
        Create a new tenant.

        Args:
            email: Unique email address for the tenant
            key_hash: Hashed authentication key for the tenant

        Returns:
            Created Tenant entity, or None if email already exists
        """
        if await self.exists_by_email(email):
            logger.warning(f"Attempted to create tenant with existing email: {email}")
            return None

        try:
            new_tenant = Tenant(id=uuid.uuid4(), email=email, key_hash=key_hash)
            self.session.add(new_tenant)
            await self.session.commit()
            await self.session.refresh(new_tenant)

            logger.info(f"Created new tenant with id: {new_tenant.id}")
            return new_tenant

        except SQLAlchemyError as e:
            logger.error(f"Failed to create tenant: {str(e)}")
            await self.session.rollback()
            return None

    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        try:
            result = await self.session.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()

            if tenant:
                logger.debug(f"Retrieved tenant by id: {tenant_id}")
            else:
                logger.debug(f"Tenant not found with id: {tenant_id}")

            return tenant

        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve tenant by id: {str(e)}")
            return None

    async def get_by_email(self, email: str) -> Optional[Tenant]:
        try:
            result = await self.session.execute(
                select(Tenant).where(Tenant.email == email)
            )
            tenant = result.scalar_one_or_none()

            if tenant:
                logger.debug(f"Retrieved tenant by email: {email}")
            else:
                logger.debug(f"Tenant not found with email: {email}")

            return tenant

        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve tenant by email: {str(e)}")
            return None

    async def update_key_hash(
        self, tenant_id: uuid.UUID, new_key_hash: str
    ) -> Optional[Tenant]:
        """
        Update the key hash for a tenant.

        Args:
            tenant_id: Unique identifier of the tenant
            new_key_hash: New hashed authentication key

        Returns:
            Updated Tenant entity, or None if tenant not found
        """
        try:
            tenant = await self.get_by_id(tenant_id)
            if not tenant:
                return None

            await self.session.execute(
                update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(key_hash=new_key_hash)
            )

            await self.session.commit()
            updated_tenant = await self.get_by_id(tenant_id)

            logger.info(f"Updated key hash for tenant: {tenant_id}")
            return updated_tenant

        except SQLAlchemyError as e:
            logger.error(f"Failed to update tenant key hash: {str(e)}")
            await self.session.rollback()
            return None

    async def delete(self, tenant_id: uuid.UUID) -> bool:
        """
        Delete a tenant and all associated data (cascade delete).

        This operation will delete the tenant and all related widgets and submissions
        due to the cascade delete configuration in the schema.

        Args:
            tenant_id: Unique identifier of the tenant to delete

        Returns:
            True if deletion was successful, False if tenant not found
        """
        try:
            tenant = await self.get_by_id(tenant_id)
            if not tenant:
                return False

            await self.session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await self.session.commit()

            logger.info(f"Deleted tenant and all associated data: {tenant_id}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to delete tenant: {str(e)}")
            await self.session.rollback()
            return False

    async def exists_by_email(self, email: str) -> bool:
        try:
            result = await self.session.execute(
                select(Tenant.id).where(Tenant.email == email)
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check tenant existence by email: {str(e)}")
            return False

    async def exists_by_id(self, tenant_id: uuid.UUID) -> bool:
        try:
            result = await self.session.execute(
                select(Tenant.id).where(Tenant.id == tenant_id)
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check tenant existence by id: {str(e)}")
            return False
