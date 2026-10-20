# Restoring the shared Message DB

All nine contexts write their events to one Message DB (the event store, on port
15433 in the Docker stack). This page lists the steps to follow after you restore
that database from a backup, in order.

Two terms come up throughout:

- **`global_position`** is the store-wide sequence number Message DB gives every
  message. A restore rolls it back along with the rows, so the next event written
  after the restore reuses positions the lost events had.
- A **checkpoint** is the stored position up to which a subscription has
  processed a stream. If a checkpoint points past the newest message the restored
  store holds (the *head*), that subscription skips every event written between
  the head and the checkpoint.

## What the steps cover, and what they do not

`protean recover --verify-checkpoints` finds checkpoints past the head, and
`--reset-beyond-head` moves them back to the head. It reads only **event-store
subscriptions**, whose checkpoints live in Message DB itself.

Every ShopStream context sets `default_subscription_type = "stream"` in its
`domain.toml`, and no handler overrides it. So today `recover` checks nothing in
ShopStream. A plain run prints `No event-store subscriptions found in domain.`
and exits 0, and a `--json` run reports `status: pass` with
`summary.checked: 0`. The step stays in the list so the procedure is right the
day a handler moves to the event store.
`verification/oracles/test_restore_checkpoints.py` moves two inventory
projectors there in test config only, and checks that the command finds, resets
and re-verifies their checkpoints.

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

### 1. Stop every engine and the API

Stop `make api`, every `make engine-<context>` and the Observatory. In the Docker
stack, `docker compose stop api engine-identity engine-catalogue ...`.

A running engine can write its old checkpoint back over a reset, and a request
can append events while you restore.

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
is clean and 1 when it finds a violation (a gap in a stream's positions, for
example). Fix any violation before you go on.

### 4. Check, and if needed reset, the checkpoints

For each context (`identity`, `catalogue`, `ordering`, `inventory`, `payments`,
`fulfillment`, `reviews`, `notifications`, `loyalty`):

```bash
PYTHONPATH=src uv run protean recover --verify-checkpoints --json --domain <context>.domain
```

The exit code tells you what to do next:

- **0**: every checkpoint is consistent. Move on.
- **1**: a row has `"verdict": "beyond_head"`, or a retry-tracking entry names a
  message the restore removed. Run the command again with `--reset-beyond-head`.
  That run exits 0 when every write succeeds. A third plain run should then exit
  0.
- **2**: the domain did not load (the message is in `data.error`), or a reset
  write failed (each failure is in `data.reset_failures`).

Keep `--json`. Without it, a domain that fails to load also exits 1, the same code
as a finding.

### 5. Rebuild lost outbox rows

```bash
make outbox-reconcile
```

It runs `protean outbox reconcile --domain <context>.domain` for each context. It
repairs a context only when that context's newest event has no outbox row. The
"Database" section of the [README](../../README.md#database) lists its limits.

### 6. Start the engines and check readiness

Start the API and the engines again. Each engine serves `/readyz` on
`127.0.0.1`, on the port its `domain.toml` sets under `[server.health]`:

| Context | Port |
|---------|------|
| identity | 8081 |
| catalogue | 8082 |
| ordering | 8083 |
| inventory | 8084 |
| payments | 8085 |
| fulfillment | 8086 |
| reviews | 8087 |
| notifications | 8088 |
| loyalty | 8089 |

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8083/readyz   # ordering
```

200 means the engine reaches its database, broker and event store. 503 means it
does not, and the `checks` block of the JSON body shows which check failed.
