import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.user import User, Organization
from app.core.config import settings

async def check_database():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=== Organizations ===")
        result = await session.execute(select(Organization))
        orgs = result.scalars().all()
        if orgs:
            for org in orgs:
                print(f"  {org.id} - {org.name}")
        else:
            print("  No organizations found")

        print("\n=== Users ===")
        result = await session.execute(select(User))
        users = result.scalars().all()
        if users:
            for user in users:
                print(f"  {user.id} - {user.email} - {user.role} - Org: {user.organization_id}")
        else:
            print("  No users found")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_database())
