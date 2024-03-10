DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS config;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS eventactions;

CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  issuperuser INTEGER DEFAULT 0 NOT NULL,
  isinitial INTEGER DEFAULT 1 NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
  key TEXT NOT NULL,
  type TEXT NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  date TEXT NOT NULL,
  minute TEXT NOT NULL,
  time TEXT NOT NULL,
  type TEXT NOT NULL,
  trigger TEXT NOT NULL,
  triggertype TEXT NOT NULL,
  triggerparam TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  actiontype TEXT NOT NULL,
  date TEXT NOT NULL,
  time TEXT NOT NULL,
  actionduration INTEGER, 
  filename TEXT NOT NULL,
  fullpath TEXT NOT NULL,
  FOREIGN KEY(event) REFERENCES events(timestamp)
);

CREATE INDEX IF NOT EXISTS events_date_idx ON events(
  date,
  minute
);

CREATE INDEX IF NOT EXISTS eventactions_type_idx ON eventactions(
  event,
  actiontype
);

