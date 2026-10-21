# Restoring the shared Message DB

All nine contexts write their events to one Message DB (the event store, on port
15433 in the Docker stack). This page lists the steps to follow after you restore
that database from a backup, in order.

Three terms come up throughout:

- **`global_position`** is the store-wide sequence number Message DB gives every
  message. A restore rolls it back along with the rows, so the next message
  written after the restore reuses positions the lost messages had.
- A **checkpoint** is the stored position up to which a subscription has
  processed a stream category (all the streams of one aggregate type, such as
  `inventory::inventory_item`).
- The **head** of a stream category is the `global_position` of the newest
  message in that category. Each category has its own head.

If a checkpoint points past its category's head, that subscription skips every
new event whose position lands between the head and the checkpoint.

## When can a checkpoint end up past the head?

A `pg_dump` reads one consistent snapshot of the database, and the checkpoint
streams live in the same Message DB as the events they name. So restoring a
`pg_dump` taken as in step 2 does not on its own leave a checkpoint past the head.
These cases do:

- **An inconsistent backup.** A file-level copy taken while the database was
  running, or a backup where the checkpoint streams were saved later than the
  event streams.
- **An engine left running.** An engine keeps its position in memory and writes
  it back after the restore, past the restored head. Step 1 prevents this.

The check in step 4 is cheap, so run it after every restore anyway.

## Which state do these steps check?

`protean recover --verify-checkpoints` finds checkpoints past the head, and
`--reset-beyond-head` moves them back to the head. It also finds
recovery-tracking entries (the failed positions a subscription retries) that
name a message the restore removed, and the reset clears them. It reads only
**event-store subscriptions**, whose checkpoints live in Message DB itself.

Every ShopStream context sets `default_subscription_type = "stream"` in its
`domain.toml`, and no handler overrides it. So today `recover` checks nothing in
ShopStream. A run without `--json` prints
`No event-store subscriptions found in domain.` and exits 0, and a `--json` run
reports `status: pass` with `summary.checked: 0`. Keep step 4 anyway: once a
handler moves to the event store, it is the step that checks that handler.
`verification/oracles/test_restore_checkpoints.py` checks that all nine contexts
report `summary.checked: 0`. It also moves three inventory projectors to the
event store in test config only, and checks that the command finds, resets and
re-verifies their checkpoints.

Restoring Message DB moves none of this state, and `recover` reads none of it:

- **Redis consumer groups.** ShopStream's handlers read Redis streams. Their
  progress is kept in Redis consumer groups, one Redis database per context
  (see the Redis DB table in `CLAUDE.md`).
- **Outbox rows.** Each context's outbox table lives in that context's Postgres
  database. Step 5 rebuilds a lost row only in the narrow case
  `make outbox-reconcile` handles (see below).
- **Read models and aggregate tables** in each context's Postgres database.

After a restore, these can name events the restored store no longer holds. No
command in this list checks them.

## Steps

### 1. Stop everything that writes events

Stop `make api`, every `make engine-<context>` and the Observatory. In the Docker
stack, `docker compose stop api engine-identity engine-catalogue ...`. Also stop
anything else that sends requests or writes events: load tests (`make loadtest`
and its variants) and seed scripts.

A running engine can write its old checkpoint back over a reset. A write between
the restore and step 4 can also hide a stale checkpoint. Once a category gets
enough new events, its head passes the stale checkpoint and `recover` reports it
consistent, but the subscription has already skipped the new events whose
positions fell between the old head and the checkpoint.

### 2. Restore the Message DB

For example, against the Docker stack's `message-db` container:

```bash
# Taking the backup
docker compose exec -T message-db pg_dump -U postgres -Fc message_store > message_store.dump

# Restoring it
docker compose exec -T message-db \
  pg_restore -U postgres -d message_store --clean --if-exists < message_store.dump
```

`pg_restore` sets the `global_position` sequence back to its value in the dump,
so the restored rows and the sequence agree.

### 3. Check the store's own consistency

```bash
make eventstore-verify
```

It is read-only and covers all nine contexts in one run. It exits 0 when the store
is clean. It exits 1 when it finds a violation (a gap in a stream's positions, for
example) or when the check fails partway through. It exits 2 when the domain does
not load. Fix any problem before you go on.

### 4. Check, and if needed reset, the checkpoints

For each context (`identity`, `catalogue`, `ordering`, `inventory`, `payments`,
`fulfillment`, `reviews`, `notifications`, `loyalty`):

```bash
PYTHONPATH=src uv run --no-sync protean recover --verify-checkpoints --json --domain <context>.domain
```

`--no-sync` uses the project's virtual environment as it is, so the run does not
replace a locally installed Protean.

Read the exit code first:

- **0**: nothing is past the head. Before you move on, also check the JSON:
  `data.summary.unknown` must be 0, and `data.summary.recovery_unknown` must be
  missing or 0. A non-zero count means `recover` could not read a checkpoint or
  a recovery-tracking stream (the store was unreachable, or a stored position is
  not a number). The command still exits 0 then, but it checked nothing for
  those subscriptions.
- **1**: a row has `"verdict": "beyond_head"`, or a recovery-tracking entry
  names a message the restore removed (it is listed under `data.recovery`). Run
  the command again with `--reset-beyond-head` added. That run exits 0 when
  every write succeeds. Then run the first command again, without
  `--reset-beyond-head`. It should exit 0.
- **2**: the domain did not load (the message is in `data.error`), or a reset
  write failed. Checkpoint failures are in `data.reset_failures`, and
  recovery-tracking failures are in `data.recovery_reset_failures`.

Keep `--json`. Without it, a domain that fails to load also exits 1, the same code
as a finding.

### 5. Rebuild lost outbox rows

```bash
make outbox-reconcile
```

It runs `protean outbox reconcile --domain <context>.domain` for each context. It
repairs a context only when that context's newest event has no outbox row. The
"Database" section of the [README](../../README.md#database) lists its limits.

The opposite case is not repaired. An outbox row still pending after the restore
can name an event the restore removed, and the engines publish it to Redis at
step 6 as if the event still existed.

### 6. Start the engines and check readiness

Start the API and the engines again. Each engine serves `/readyz` on the port
its `domain.toml` sets under `[server.health]`. It binds `127.0.0.1` unless
`PROTEAN_HEALTH_HOST` is set; the Docker engines set it to `0.0.0.0`. An empty
`PROTEAN_HEALTH_HOST` binds every interface, so leave it unset on a laptop.

| Context | Port |
|---------|------|
| identity | 8100 |
| catalogue | 8110 |
| ordering | 8120 |
| inventory | 8130 |
| payments | 8140 |
| fulfillment | 8150 |
| reviews | 8160 |
| notifications | 8170 |
| loyalty | 8180 |

`port_auto_increment` is on, so with `--workers N` the first worker to start
takes the base port and each other worker takes the next free port above it.
Each worker logs `Health check server listening on ...` with the port it bound.
Every worker answers for itself, so check each one.

For an engine started with `make engine-<context>` on your machine:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8120/readyz   # ordering
```

The Docker stack publishes no engine ports, so run `curl` inside the container:

```bash
docker compose exec engine-ordering \
  curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8120/readyz
```

200 means the engine reaches its databases, brokers, event store and caches
(loyalty also uses a Redis cache on DB 9). 503 means one of those checks failed,
or the engine is draining or shutting down. The `checks` block of the JSON body
shows which.
