import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from aura.core.enums import UserRole
from aura.core.security import hash_password
from aura.db.models import User
from aura.db.session import AsyncSessionFactory, close_database


async def create_admin(email: str, full_name: str, password: str) -> None:
    async with AsyncSessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            user = User(
                email=email.lower(),
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
            session.add(user)
        else:
            user.role = UserRole.ADMIN
            user.password_hash = hash_password(password)
            user.is_active = True
        await session.commit()
    await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote a TaxAura administrator.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Admin password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    asyncio.run(create_admin(args.email, args.name, password))
    print("Administrator is ready.")


if __name__ == "__main__":
    main()
