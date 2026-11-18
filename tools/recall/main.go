// recall: search everything the user has said and done with Claude, locally.
//
//	recall index [--full]                      (re)index the sources; only changed files are read again
//	recall search QUERY [--source code|web|steno|notes] [--project NAME] [--since YYYY-MM-DD] [--role R] [--limit N]
//	recall show ID [--context N]               a unit with N units before and after it (default 3)
//	recall stats                               counts per source, database size
//
// Sources: Claude Code transcripts ($RECALL_CLAUDE, ~/.claude/projects), claude.ai exports in the manager's inbox
// ($RECALL_MANAGER/inbox: *.zip or conversations.json), stenographr notes ($RECALL_STENO, /data/transcripts),
// the manager's notes ($RECALL_MANAGER, ~/manager). Database: $RECALL_DB or ~/.local/share/hyperbeam/recall.db.
// No network. Secret-looking strings are masked before they are stored and when printed.
package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

func home() string { h, _ := os.UserHomeDir(); return h }

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func dbPath() string {
	if p := os.Getenv("RECALL_DB"); p != "" {
		return p
	}
	d := os.Getenv("XDG_DATA_HOME")
	if d == "" {
		d = filepath.Join(home(), ".local", "share")
	}
	return filepath.Join(d, "hyperbeam", "recall.db")
}

func openDB() (*sql.DB, error) {
	p := dbPath()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", "file:"+p+"?_pragma=busy_timeout(30000)&_pragma=journal_mode(WAL)&_pragma=synchronous(OFF)")
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`
CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INTEGER, mtime INTEGER, off INTEGER, tail TEXT);
CREATE TABLE IF NOT EXISTS units(id INTEGER PRIMARY KEY, file TEXT, grp TEXT, seq INTEGER, source TEXT, project TEXT, session TEXT, title TEXT, role TEXT, ts INTEGER);
CREATE INDEX IF NOT EXISTS units_file ON units(file);
CREATE INDEX IF NOT EXISTS units_grp ON units(grp, seq);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(text, tokenize='porter unicode61');`)
	if err == nil {
		db.Exec(`ALTER TABLE files ADD COLUMN tail TEXT`) // a database made before the column existed; fails harmlessly when it is there
	}
	return db, err
}

func main() {
	args := os.Args[1:]
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" {
		fmt.Println(strings.TrimSpace(`usage:
  recall index [--full]
  recall search QUERY [--source code|web|steno|notes] [--project NAME] [--since YYYY-MM-DD] [--role R] [--limit N]
  recall show ID [--context N]
  recall stats
Searches Claude Code transcripts, claude.ai exports (manager inbox), stenographr notes and the manager's notes. Local only.`))
		return
	}
	if args[0] == "--version" || args[0] == "version" {
		fmt.Println("recall 1.0")
		return
	}
	db, err := openDB()
	if err != nil {
		die(err)
	}
	defer db.Close()
	switch args[0] {
	case "index":
		full := len(args) > 1 && args[1] == "--full"
		t := time.Now()
		st, err := reindex(db, full)
		if err != nil {
			die(err)
		}
		fmt.Printf("indexed %d files (%d unchanged, %d removed), %d units, in %s\n", st.changed, st.same, st.removed, st.units, time.Since(t).Round(time.Millisecond))
	case "search":
		cmdSearch(db, args[1:])
	case "show":
		cmdShow(db, args[1:])
	case "stats":
		cmdStats(db)
	default:
		fmt.Fprintf(os.Stderr, "recall: unknown command %q (recall help)\n", args[0])
		os.Exit(2)
	}
}

func die(err error) {
	fmt.Fprintln(os.Stderr, "recall:", err)
	os.Exit(1)
}

func atoi(s string, d int) int {
	if n, err := strconv.Atoi(s); err == nil {
		return n
	}
	return d
}
