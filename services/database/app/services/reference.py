"""Reference data shared by every role.

The lists a student needs to fill in an application: the partner
institutions they may choose from (FR-02) and the coordinators who can be
assigned (BR-03).  Only active institutions are offered, so a retired
partner stops being selectable without affecting past applications.

Thin over the repository today, but it is the layer that owns the
question "what may a student choose?", and the answer is a rule rather
than a query -- the ``active_only`` filter is already one.
"""

from .. import repositories as repo


def list_institutions():
    return repo.list_institutions(active_only=True)


def list_coordinators():
    return repo.list_coordinators()
