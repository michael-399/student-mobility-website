"""Tests for the development seed."""

import pytest

from app.database import db
from app.models import Institution, UserAccount, UserRole
from seeds import dev_seed


class TestSeedData:
    def test_every_role_is_represented(self):
        roles = {role for _, _, role in dev_seed.USERS}

        assert roles == set(UserRole)

    def test_accounts_have_distinct_emails(self):
        emails = [email for email, _, _ in dev_seed.USERS]

        assert len(set(emails)) == len(emails)

    def test_institutions_are_distinct(self):
        assert len(set(dev_seed.INSTITUTIONS)) == len(dev_seed.INSTITUTIONS)


class TestNameSplitting:
    @pytest.mark.parametrize(
        "full_name,expected",
        [
            ("Alice Student", ("Alice", "Student")),
            ("Dr. Smith", ("Dr.", "Smith")),
            ("Prof. Jones", ("Prof.", "Jones")),
            ("Office Admin", ("Office", "Admin")),
        ],
    )
    def test_rejoins_to_the_original(self, full_name, expected):
        """Rendered as "first last", the name reads exactly as before."""
        first, last = dev_seed.split_name(full_name)

        assert (first, last) == expected
        assert f"{first} {last}" == full_name

    def test_a_single_word_name_fills_both_columns(self):
        """Both columns are NOT NULL, so neither may end up empty."""
        first, last = dev_seed.split_name("Madonna")

        assert first and last


class TestSeeding:
    @pytest.fixture
    def seeded(self, session):
        dev_seed.seed()

        yield

        emails = [email for email, _, _ in dev_seed.USERS]
        names = [name for name, _, _ in dev_seed.INSTITUTIONS]
        session.rollback()
        session.execute(db.delete(UserAccount).where(UserAccount.email.in_(emails)))
        session.execute(db.delete(Institution).where(Institution.name.in_(names)))
        session.commit()

    def test_creates_every_account(self, seeded, session):
        for email, full_name, role in dev_seed.USERS:
            user = session.execute(
                db.select(UserAccount).where(UserAccount.email == email)
            ).scalar_one()

            assert user.user_role is role
            assert f"{user.first_name} {user.last_name}" == full_name

    def test_creates_every_institution(self, seeded, session):
        for name, country, city in dev_seed.INSTITUTIONS:
            institution = session.execute(
                db.select(Institution).where(Institution.name == name)
            ).scalar_one()

            assert institution.country == country
            assert institution.city == city
            assert institution.is_active is True

    def test_running_twice_adds_nothing(self, seeded, session):
        before = session.execute(
            db.select(db.func.count()).select_from(UserAccount)
        ).scalar_one()

        dev_seed.seed()

        after = session.execute(
            db.select(db.func.count()).select_from(UserAccount)
        ).scalar_one()

        assert after == before

    def test_every_account_can_log_in(self, seeded, app):
        """The whole point of the seed: these credentials work."""
        client = app.test_client()

        for email, _, role in dev_seed.USERS:
            response = client.post(
                "/api/login",
                json={"email": email, "password": dev_seed.DEFAULT_PASSWORD},
            )

            assert response.status_code == 200, email
            assert response.get_json()["user"]["role"] == role.value
