package main

import (
	"database/sql"
	"fmt"
	"os"
	"strings"
	"time"
)

var sourceNames = map[string]string{"code": "code", "web": "web", "steno": "steno", "notes": "notes"}

// ftsQuery turns plain words into a safe FTS5 query: each word quoted (a trailing * keeps prefix matching),
// quoted phrases kept, AND / OR / NOT kept as operators.
func ftsQuery(q string) string {
	var out []string
	rest := q
	for {
		rest = strings.TrimLeft(rest, " \t")
		if rest == "" {
			break
		}
		var tok string
		if rest[0] == '"' {
			end := strings.IndexByte(rest[1:], '"')
			if end < 0 {
				tok, rest = rest[1:], ""
			} else {
				tok, rest = rest[1:1+end], rest[end+2:]
			}
			if t := strings.ReplaceAll(tok, `"`, ""); strings.TrimSpace(t) != "" {
				out = append(out, `"`+t+`"`)
			}
			continue
		}
		i := strings.IndexAny(rest, " \t")
		if i < 0 {
			tok, rest = rest, ""
		} else {
			tok, rest = rest[:i], rest[i:]
		}
		if tok == "AND" || tok == "OR" || tok == "NOT" {
			out = append(out, tok)
			continue
		}
		star := strings.HasSuffix(tok, "*")
		t := strings.ReplaceAll(strings.TrimRight(tok, "*"), `"`, "")
		if strings.TrimSpace(t) == "" {
			continue
		}
		w := `"` + t + `"`
		if star {
			w += "*"
		}
		out = append(out, w)
	}
	return strings.Join(out, " ")
}

func cmdSearch(db *sql.DB, args []string) {
	var words []string
	source, project, since, role, limit := "", "", "", "", 10
	for i := 0; i < len(args); i++ {
		next := func() string {
			if i+1 < len(args) {
				i++
				return args[i]
			}
			return ""
		}
		switch args[i] {
		case "--source":
			source = next()
		case "--project":
			project = next()
		case "--since":
			since = next()
		case "--role":
			role = next()
		case "--limit":
			limit = atoi(next(), 10)
		default:
			words = append(words, args[i])
		}
	}
	q := ftsQuery(strings.Join(words, " "))
	if q == "" {
		fmt.Fprintln(os.Stderr, "usage: recall search QUERY [--source code|web|steno|notes] [--project NAME] [--since YYYY-MM-DD] [--role R] [--limit N]")
		os.Exit(2)
	}
	if source != "" && sourceNames[source] == "" {
		die(fmt.Errorf("--source must be code, web, steno or notes"))
	}
	if !quiet() {
		if st, err := reindex(db, false); err != nil {
			fmt.Fprintln(os.Stderr, "recall: index:", err)
		} else if st.changed > 0 {
			fmt.Fprintf(os.Stderr, "(index was stale: %d files read again)\n", st.changed)
		}
	}
	sqlq := `SELECT u.id, u.ts, u.source, u.project, u.title, u.role, snippet(fts, 0, '[', ']', '…', 22)
FROM fts JOIN units u ON u.id = fts.rowid WHERE fts MATCH ?`
	a := []any{q}
	if source != "" {
		sqlq += " AND u.source = ?"
		a = append(a, source)
	}
	if project != "" {
		sqlq += " AND lower(u.project) LIKE ?"
		a = append(a, "%"+strings.ToLower(project)+"%")
	}
	if since != "" {
		t, err := time.ParseInLocation("2006-01-02", since, time.Local)
		if err != nil {
			die(fmt.Errorf("--since wants YYYY-MM-DD"))
		}
		sqlq += " AND u.ts >= ?"
		a = append(a, t.Unix())
	}
	if role != "" {
		sqlq += " AND u.role = ?"
		a = append(a, role)
	} else {
		sqlq += " AND u.role != 'tool'"
	}
	sqlq += " ORDER BY bm25(fts) LIMIT ?"
	a = append(a, limit)
	rows, err := db.Query(sqlq, a...)
	if err != nil {
		die(err)
	}
	defer rows.Close()
	n := 0
	for rows.Next() {
		var id, ts int64
		var src, proj, title, rl, snip string
		if err := rows.Scan(&id, &ts, &src, &proj, &title, &rl, &snip); err != nil {
			die(err)
		}
		n++
		where := proj
		if title != "" && title != proj {
			if where != "" {
				where += " / "
			}
			where += title
		}
		fmt.Printf("#%d  %s  %s  %s  %s\n    %s\n", id, fmtTS(ts), src, rl, where, mask(oneLine(snip)))
	}
	if n == 0 {
		fmt.Println("no matches")
	} else {
		fmt.Println("(recall show ID to read around one)")
	}
}

func quiet() bool { return os.Getenv("RECALL_NO_AUTOINDEX") != "" }

func oneLine(s string) string { return strings.Join(strings.Fields(s), " ") }

func fmtTS(ts int64) string {
	if ts == 0 {
		return "----------"
	}
	return time.Unix(ts, 0).Format("2006-01-02 15:04")
}

func cmdShow(db *sql.DB, args []string) {
	id, ctx := int64(0), 3
	for i := 0; i < len(args); i++ {
		switch {
		case args[i] == "--context" && i+1 < len(args):
			i++
			ctx = atoi(args[i], 3)
		default:
			id = int64(atoi(strings.TrimPrefix(args[i], "#"), 0))
		}
	}
	if id == 0 {
		fmt.Fprintln(os.Stderr, "usage: recall show ID [--context N]")
		os.Exit(2)
	}
	var grp string
	var seq int64
	if err := db.QueryRow(`SELECT grp, seq FROM units WHERE id=?`, id).Scan(&grp, &seq); err != nil {
		die(fmt.Errorf("no unit #%d", id))
	}
	rows, err := db.Query(`SELECT u.id, u.ts, u.source, u.project, u.title, u.role, u.session, fts.text FROM units u JOIN fts ON fts.rowid=u.id
WHERE u.grp=? AND u.seq BETWEEN ? AND ? ORDER BY u.seq`, grp, seq-int64(ctx), seq+int64(ctx))
	if err != nil {
		die(err)
	}
	defer rows.Close()
	for rows.Next() {
		var uid, ts int64
		var src, proj, title, rl, sess, text string
		if err := rows.Scan(&uid, &ts, &src, &proj, &title, &rl, &sess, &text); err != nil {
			die(err)
		}
		mark, limit := "  ", 1500
		if uid == id {
			mark, limit = "▶ ", 12000
		}
		if r := []rune(text); len(r) > limit {
			text = string(r[:limit]) + fmt.Sprintf(" … [%d more characters]", len(r)-limit)
		}
		fmt.Printf("%s#%d  %s  %s  %s  %s %s\n%s\n\n", mark, uid, fmtTS(ts), src, rl, proj, title, mask(strings.TrimSpace(text)))
	}
}

func cmdStats(db *sql.DB) {
	rows, err := db.Query(`SELECT source, count(*), min(ts), max(ts) FROM units GROUP BY source`)
	if err != nil {
		die(err)
	}
	defer rows.Close()
	for rows.Next() {
		var s string
		var n, lo, hi int64
		rows.Scan(&s, &n, &lo, &hi)
		fmt.Printf("%-6s %8d units  %s .. %s\n", s, n, fmtTS(lo)[:10], fmtTS(hi)[:10])
	}
	if fi, err := os.Stat(dbPath()); err == nil {
		fmt.Printf("database %s (%.1f MB)\n", dbPath(), float64(fi.Size())/1e6)
	}
}
