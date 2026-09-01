"""Development seed data.

Five accounts sharing one password and eight partner institutions, enough
to demo every role.

Idempotent -- matching on the natural keys the schema already enforces
unique (a user's email, an institution's name/country/city) -- so running
it repeatedly updates rather than duplicates, and it is safe to run on
every container start.

Run from ``services/database``::

    python -m seeds.dev_seed
"""

from app import create_app
from app.database import db
from app.models import Institution, UserAccount, UserRole
from app.security import hash_password

# Development only.  Every seeded account shares this password.
DEFAULT_PASSWORD = "password"

# (email, full name, role). Each name is split on its first space into
# the first/last name columns, so "Dr. Smith" keeps its title.
USERS = (
    ("student@test.com", "Alice Student", UserRole.STUDENT),
    ("student2@test.com", "Bob Student", UserRole.STUDENT),
    ("lecturer@test.com", "Dr. Smith", UserRole.COORDINATOR),
    ("lecturer2@test.com", "Prof. Jones", UserRole.COORDINATOR),
    ("office@test.com", "Office Admin", UserRole.OFFICE_STAFF),
)

INSTITUTIONS = (
    ("University of Barcelona", "Spain", "Barcelona"),
    ("TU Berlin", "Germany", "Berlin"),
    ("Sorbonne University", "France", "Paris"),
    ("University of Oslo", "Norway", "Oslo"),
    ("University of Tokyo", "Japan", "Tokyo"),
    ("KU Leuven", "Belgium", "Leuven"),
    ("ETH Zurich", "Switzerland", "Zurich"),
    ("University College Dublin", "Ireland", "Dublin"),
)


def split_name(full_name: str) -> tuple[str, str]:
    """Split a single name into the first and last name columns.

    On the first space only, so "Dr. Smith" keeps its title with the
    first name and renders back unchanged.
    """
    first, _, last = full_name.partition(" ")

    return (first, last or first)


def seed_users(password_hash: str) -> int:
    created = 0

    for email, full_name, role in USERS:
        first_name, last_name = split_name(full_name)
        attributes = {
            "first_name": first_name,
            "last_name": last_name,
            "user_role": role,
            "password_hash": password_hash,
        }

        user = db.session.execute(
            db.select(UserAccount).where(UserAccount.email == email)
        ).scalar_one_or_none()

        if user is None:
            db.session.add(UserAccount(email=email, **attributes))
            created += 1
        else:
            for field, value in attributes.items():
                setattr(user, field, value)

    return created


def seed_institutions() -> int:
    created = 0

    for name, country, city in INSTITUTIONS:
        institution = db.session.execute(
            db.select(Institution).where(
                Institution.name == name,
                Institution.country == country,
                Institution.city == city,
            )
        ).scalar_one_or_none()

        if institution is None:
            db.session.add(Institution(name=name, country=country, city=city))
            created += 1
        else:
            # A partner retired in an earlier run comes back selectable.
            institution.is_active = True

    return created


def seed() -> None:
    # Hashed once and shared: Argon2 is deliberately slow, and every
    # seeded account uses the same development password anyway.
    password_hash = hash_password(DEFAULT_PASSWORD)

    new_users = seed_users(password_hash)
    new_institutions = seed_institutions()

    db.session.commit()

    print(
        f"Seeded {len(USERS)} users ({new_users} new) "
        f"and {len(INSTITUTIONS)} institutions ({new_institutions} new)."
    )
    print(f'All accounts use the password "{DEFAULT_PASSWORD}".')


def main() -> None:
    app = create_app()

    with app.app_context():
        seed()


if __name__ == "__main__":
    main()
