CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT     NOT NULL,
    email         TEXT     NOT NULL,
    url           TEXT     NOT NULL,
    severity      TEXT     NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
    problem_time  TEXT     NOT NULL,
    description   TEXT     NOT NULL,
    status        TEXT     NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','In Progress','Pending','Closed')),
    submitted_at  TEXT     NOT NULL
);
