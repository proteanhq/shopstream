"""Custom Postgres database model for :class:`RewardAccountView`.

Exercises Protean's ``@database_model`` capability — a hand-written SQLAlchemy model that
overrides the columns Protean would otherwise auto-generate for a projection. It is registered
with ``database="postgresql"`` so that **only the Postgres provider** uses it; the ``memory``
test environment falls back to Protean's auto-generated model (so both CI jobs stay green).

Customisations vs. the auto-generated model:

* ``customer_id`` → ``Text`` **with an index** — the projection is looked up per account today,
  but a custom model lets us index the customer column for efficient "all accounts for a
  customer" scans, and drops the arbitrary ``String`` length cap.
* ``member_code`` → ``Text`` — membership codes are opaque, unbounded identifiers; ``Text``
  avoids a length limit.

Only the overridden columns are declared here; Protean auto-maps the rest of the projection's
fields (``account_id``, ``tier``, ``status``, ``points_balance``, ``lifetime_points``,
``updated_at``). Model field names must be a subset of the projection's declared fields.
"""

from protean.core.database_model import BaseDatabaseModel
from sqlalchemy import Column, Text

from loyalty.domain import loyalty
from loyalty.projections.reward_account_view import RewardAccountView


@loyalty.database_model(part_of=RewardAccountView, database="postgresql")
class RewardAccountViewPostgresModel(BaseDatabaseModel):
    customer_id = Column(Text, index=True)
    member_code = Column(Text)
