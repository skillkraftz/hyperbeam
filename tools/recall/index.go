package main

import (
	"archive/zip"
	"bufio"
	"crypto/sha1"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

type unit struct {
	grp, source, project, session, title, role string
	ts                                         int64
	text                                       string
}

type fileInfo struct {
	path, kind, project string
	size, mtime         int64
}

type parsed struct {
	fi    fileInfo
	units []unit
	off   int64
	tail  string // hash of the bytes just before off (a Claude Code file): tells a file that grew from one that was rewritten
	appnd bool   // units are to be added after the file's existing ones
	err   error
}

type stats struct{ changed, same, removed, units int }

const maxText = 20000
const maxTool = 2000

func discover() []fileInfo {
	var out []fileInfo
	add := func(p, kind, project string, d fs.DirEntry) {
		if info, err := d.Info(); err == nil {
			out = append(out, fileInfo{p, kind, project, info.Size(), info.ModTime().UnixNano()})
		}
	}
	croot := envOr("RECALL_CLAUDE", filepath.Join(home(), ".claude", "projects"))
	filepath.WalkDir(croot, func(p string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() && strings.HasSuffix(p, ".jsonl") {
			rel, _ := filepath.Rel(croot, p)
			add(p, "code", projectName(strings.Split(rel, string(filepath.Separator))[0]), d)
		}
		return nil
	})
	sroot := envOr("RECALL_STENO", "/data/transcripts")
	for _, g := range []string{filepath.Join(sroot, "steno-*.txt"), filepath.Join(sroot, "clips", "*.txt")} {
		ms, _ := filepath.Glob(g)
		for _, p := range ms {
			if d, err := os.Lstat(p); err == nil {
				add(p, "steno", "stenographr", fs.FileInfoToDirEntry(d))
			}
		}
	}
	mroot := envOr("RECALL_MANAGER", filepath.Join(home(), "manager"))
	inbox := filepath.Join(mroot, "inbox")
	filepath.WalkDir(mroot, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(mroot, p)
		if d.IsDir() {
			if p != mroot && (strings.HasPrefix(d.Name(), ".") || d.Name() == "node_modules") {
				return filepath.SkipDir
			}
			if strings.HasPrefix(p, inbox) && strings.Count(rel, string(filepath.Separator)) > 3 {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.HasPrefix(p, inbox+string(filepath.Separator)) {
			if strings.HasSuffix(p, ".zip") || d.Name() == "conversations.json" {
				add(p, "web", "", d)
			}
		} else if strings.HasSuffix(p, ".md") {
			proj := "manager"
			if strings.HasPrefix(rel, "projects"+string(filepath.Separator)) {
				proj = strings.TrimSuffix(filepath.Base(p), ".md")
			}
			add(p, "notes", proj, d)
		}
		return nil
	})
	return out
}

// projectName: Claude Code's folder name is the working directory with non-alphanumerics as "-".
func projectName(dir string) string {
	n := strings.TrimPrefix(dir, "-home-")
	if i := strings.IndexByte(n, '-'); i >= 0 && n != dir {
		n = n[i+1:] // drop the user name
	}
	n = strings.TrimPrefix(n, "projects-")
	n = strings.TrimLeft(n, "-")
	if n == "" || n == dir && !strings.HasPrefix(dir, "-") {
		return dir
	}
	return n
}

func reindex(db *sql.DB, full bool) (stats, error) {
	var st stats
	type oldFile struct {
		size, mtime, off int64
		tail             string
	}
	old := map[string]oldFile{}
	rows, err := db.Query(`SELECT path, size, mtime, off, coalesce(tail,'') FROM files`)
	if err != nil {
		return st, err
	}
	for rows.Next() {
		var p string
		var v oldFile
		rows.Scan(&p, &v.size, &v.mtime, &v.off, &v.tail)
		old[p] = v
	}
	rows.Close()

	found := discover()
	seen := map[string]bool{}
	var todo []fileInfo
	isWeb := func(p string) bool { return strings.HasSuffix(p, ".zip") || filepath.Base(p) == "conversations.json" }
	webGone := false // a removed export may have been the copy that won the dedupe below: the others are read again
	for p := range old {
		if !seenPath(found, p) && isWeb(p) {
			webGone = true
		}
	}
	for _, f := range found {
		seen[f.path] = true
		o, ok := old[f.path]
		if !full && !(webGone && f.kind == "web") && ok && o.size == f.size && o.mtime == f.mtime {
			st.same++
			continue
		}
		todo = append(todo, f)
	}
	var gone []string
	for p := range old {
		if !seen[p] {
			gone = append(gone, p)
		}
	}
	if len(todo) == 0 && len(gone) == 0 {
		return st, nil
	}

	results := make(chan parsed, 8)
	var wg sync.WaitGroup
	sem := make(chan struct{}, 12)
	for _, f := range todo {
		o, ok := old[f.path]
		start := int64(0)
		if !full && ok && f.kind == "code" && f.size > o.size && o.off > 0 && o.tail != "" && o.tail == tailHash(f.path, o.off) {
			start = o.off // grew, and the bytes before the old end are the ones read last time
		}
		wg.Add(1)
		go func(f fileInfo, start int64) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			results <- parseFile(f, start)
		}(f, start)
	}
	go func() { wg.Wait(); close(results) }()

	tx, err := db.Begin()
	if err != nil {
		return st, err
	}
	defer tx.Rollback()
	for _, p := range gone {
		dropFile(tx, p)
		st.removed++
	}
	insU, _ := tx.Prepare(`INSERT INTO units(file,grp,seq,source,project,session,title,role,ts) VALUES(?,?,?,?,?,?,?,?,?)`)
	insF, _ := tx.Prepare(`INSERT INTO fts(rowid,text) VALUES(?,?)`)
	for r := range results {
		if r.err != nil {
			continue // unreadable or half-written file: left as it was, tried again next time
		}
		seq := int64(0)
		if r.appnd {
			tx.QueryRow(`SELECT coalesce(max(seq),0) FROM units WHERE file=?`, r.fi.path).Scan(&seq)
		} else {
			dropFile(tx, r.fi.path)
		}
		for _, u := range r.units {
			seq++
			res, err := insU.Exec(r.fi.path, u.grp, seq, u.source, u.project, u.session, u.title, u.role, u.ts)
			if err != nil {
				return st, err
			}
			id, _ := res.LastInsertId()
			if _, err := insF.Exec(id, u.text); err != nil {
				return st, err
			}
			st.units++
		}
		tx.Exec(`INSERT OR REPLACE INTO files(path,size,mtime,off,tail) VALUES(?,?,?,?,?)`, r.fi.path, r.fi.size, r.fi.mtime, r.off, r.tail)
		st.changed++
	}
	// The same claude.ai export can sit in the inbox twice (the zip and its unpacked conversations.json): one copy per conversation id stays, the first path.
	dupe := `source='web' AND file != (SELECT min(file) FROM units u2 WHERE u2.source='web' AND u2.session=units.session)`
	tx.Exec(`DELETE FROM fts WHERE rowid IN (SELECT id FROM units WHERE ` + dupe + `)`)
	if res, err := tx.Exec(`DELETE FROM units WHERE ` + dupe); err == nil {
		if n, _ := res.RowsAffected(); n > 0 {
			st.units -= int(n)
		}
	}
	return st, tx.Commit()
}

func seenPath(found []fileInfo, p string) bool {
	for _, f := range found {
		if f.path == p {
			return true
		}
	}
	return false
}

func dropFile(tx *sql.Tx, p string) {
	tx.Exec(`DELETE FROM fts WHERE rowid IN (SELECT id FROM units WHERE file=?)`, p)
	tx.Exec(`DELETE FROM units WHERE file=?`, p)
	tx.Exec(`DELETE FROM files WHERE path=?`, p)
}

func parseFile(f fileInfo, start int64) parsed {
	p := parsed{fi: f, appnd: start > 0}
	var err error
	switch f.kind {
	case "code":
		p.units, p.off, err = parseClaude(f, start)
		if err == nil {
			p.tail = tailHash(f.path, p.off)
		}
	case "steno":
		p.units, err = parseSteno(f)
	case "notes":
		p.units, err = parseNotes(f)
	case "web":
		p.units, err = parseWeb(f)
	}
	p.err = err
	return p
}

// tailHash: a hash of the (up to 4 KB of) bytes that end at off; "" if the file is shorter or unreadable.
func tailHash(path string, off int64) string {
	fh, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer fh.Close()
	n := int64(4096)
	if off < n {
		n = off
	}
	buf := make([]byte, n)
	if _, err := fh.ReadAt(buf, off-n); err != nil {
		return ""
	}
	h := sha1.Sum(buf)
	return hex.EncodeToString(h[:])
}

func clip(s string, n int) string {
	if r := []rune(s); len(r) > n {
		return string(r[:n])
	}
	return s
}

func parseTime(s string) int64 {
	for _, l := range []string{time.RFC3339Nano, time.RFC3339} {
		if t, err := time.Parse(l, s); err == nil {
			return t.Unix()
		}
	}
	return 0
}

// ---- Claude Code: ~/.claude/projects/<project>/<session>.jsonl

type cline struct {
	Type      string `json:"type"`
	Timestamp string `json:"timestamp"`
	SessionID string `json:"sessionId"`
	IsMeta    bool   `json:"isMeta"`
	Message   struct {
		Role    string          `json:"role"`
		Content json.RawMessage `json:"content"`
	} `json:"message"`
}

type cblock struct {
	Type    string          `json:"type"`
	Text    string          `json:"text"`
	Name    string          `json:"name"`
	Content json.RawMessage `json:"content"`
}

func parseClaude(f fileInfo, start int64) ([]unit, int64, error) {
	fh, err := os.Open(f.path)
	if err != nil {
		return nil, 0, err
	}
	defer fh.Close()
	if start > 0 {
		fh.Seek(start, io.SeekStart)
	}
	rd := bufio.NewReaderSize(fh, 1<<20)
	sess := strings.TrimSuffix(filepath.Base(f.path), ".jsonl")
	var out []unit
	off := start
	for {
		line, err := rd.ReadBytes('\n')
		if err != nil && len(line) > 0 && line[len(line)-1] != '\n' {
			break // an incomplete last line: read it next time
		}
		off += int64(len(line))
		if len(line) > 1 {
			var c cline
			if json.Unmarshal(line, &c) == nil && (c.Type == "user" || c.Type == "assistant") && !c.IsMeta {
				role := c.Type
				text := extract(c.Message.Content, &role)
				if strings.TrimSpace(text) != "" {
					out = append(out, unit{grp: f.path, source: "code", project: f.project, session: sess[:min(8, len(sess))], role: role, ts: parseTime(c.Timestamp), text: clip(mask(text), maxText)})
				}
			}
		}
		if err != nil {
			break
		}
	}
	return out, off, nil
}

// extract: the text of a message. Tool calls keep only their name; a tool result is kept when short (role becomes "tool").
func extract(raw json.RawMessage, role *string) string {
	var s string
	if json.Unmarshal(raw, &s) == nil {
		return s
	}
	var blocks []cblock
	if json.Unmarshal(raw, &blocks) != nil {
		return ""
	}
	var parts []string
	onlyResult := len(blocks) > 0
	for _, b := range blocks {
		switch b.Type {
		case "text":
			parts = append(parts, b.Text)
			onlyResult = false
		case "tool_use":
			parts = append(parts, "["+b.Name+"]")
			onlyResult = false
		case "tool_result":
			t := resultText(b.Content)
			if len([]rune(t)) <= maxTool {
				parts = append(parts, t)
			}
		default:
			onlyResult = false
		}
	}
	if onlyResult {
		*role = "tool"
	}
	return strings.Join(parts, "\n")
}

func resultText(raw json.RawMessage) string {
	var s string
	if json.Unmarshal(raw, &s) == nil {
		return s
	}
	var bs []cblock
	if json.Unmarshal(raw, &bs) == nil {
		var t []string
		for _, b := range bs {
			if b.Type == "text" {
				t = append(t, b.Text)
			}
		}
		return strings.Join(t, "\n")
	}
	return ""
}

// ---- stenographr: steno-DATE.txt ("start: DATE TIME ..." then "[HH:MM:SS] text") and clips/*.txt ("recorded DATE TIME", "[.. | HH:MM:SS] text")

var (
	reDate  = regexp.MustCompile(`(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?`)
	reStamp = regexp.MustCompile(`^\[(?:[^\]|]*\|\s*)?(\d{2}:\d{2}:\d{2})\]\s*(.*)$`)
)

func parseSteno(f fileInfo) ([]unit, error) {
	b, err := os.ReadFile(f.path)
	if err != nil {
		return nil, err
	}
	name := strings.TrimSuffix(filepath.Base(f.path), ".txt")
	date := ""
	if m := reDate.FindStringSubmatch(name); m != nil {
		date = m[1]
	}
	var out []unit
	var grp []string
	var gts int64
	flush := func() {
		if len(grp) > 0 {
			out = append(out, unit{grp: f.path, source: "steno", project: "stenographr", session: name, title: name, role: "note", ts: gts, text: mask(strings.Join(grp, "\n"))})
			grp = nil
		}
	}
	for _, l := range strings.Split(string(b), "\n") {
		l = strings.TrimSpace(l)
		if l == "" {
			continue
		}
		if !strings.HasPrefix(l, "[") {
			if strings.Contains(l, "start:") || strings.Contains(l, "recorded") {
				if m := reDate.FindStringSubmatch(l); m != nil {
					date = m[1]
				}
			}
			continue
		}
		m := reStamp.FindStringSubmatch(l)
		if m == nil || strings.TrimSpace(m[2]) == "" {
			continue
		}
		if len(grp) == 0 {
			if t, err := time.ParseInLocation("2006-01-02 15:04:05", date+" "+m[1], time.Local); err == nil {
				gts = t.Unix()
			} else {
				gts = f.mtime / 1e9
			}
		}
		grp = append(grp, m[1]+" "+m[2])
		if len(grp) >= 5 {
			flush()
		}
	}
	flush()
	return out, nil
}

// ---- the manager's notes: one unit per section (a heading starts one)

func parseNotes(f fileInfo) ([]unit, error) {
	b, err := os.ReadFile(f.path)
	if err != nil {
		return nil, err
	}
	base := filepath.Base(f.path)
	ts := f.mtime / 1e9
	var out []unit
	title, inCode := base, false
	var cur []string
	flush := func() {
		if t := strings.TrimSpace(strings.Join(cur, "\n")); t != "" {
			out = append(out, unit{grp: f.path, source: "notes", project: f.project, session: base, title: mask(title), role: "note", ts: ts, text: clip(mask(t), maxText)})
		}
		cur = nil
	}
	for _, l := range strings.Split(string(b), "\n") {
		if strings.HasPrefix(l, "```") {
			inCode = !inCode
		}
		if !inCode && strings.HasPrefix(l, "#") {
			flush()
			title = base + " / " + strings.TrimSpace(strings.TrimLeft(l, "#"))
		}
		cur = append(cur, l)
	}
	flush()
	return out, nil
}

// ---- claude.ai export: conversations.json (a list of conversations with chat_messages), loose or inside a zip

type wconv struct {
	UUID      string `json:"uuid"`
	Name      string `json:"name"`
	CreatedAt string `json:"created_at"`
	Messages  []struct {
		Sender    string `json:"sender"`
		Text      string `json:"text"`
		CreatedAt string `json:"created_at"`
		Content   []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	} `json:"chat_messages"`
}

func parseWeb(f fileInfo) ([]unit, error) {
	var data []byte
	var err error
	if strings.HasSuffix(f.path, ".zip") {
		zr, e := zip.OpenReader(f.path)
		if e != nil {
			return nil, e
		}
		defer zr.Close()
		for _, zf := range zr.File {
			if filepath.Base(zf.Name) == "conversations.json" {
				rc, e := zf.Open()
				if e != nil {
					return nil, e
				}
				data, err = io.ReadAll(rc)
				rc.Close()
			}
		}
		if data == nil {
			return nil, nil
		}
	} else {
		data, err = os.ReadFile(f.path)
	}
	if err != nil {
		return nil, err
	}
	var convs []wconv
	if err := json.Unmarshal(data, &convs); err != nil {
		return nil, err
	}
	sort.SliceStable(convs, func(i, j int) bool { return convs[i].CreatedAt < convs[j].CreatedAt })
	var out []unit
	for _, c := range convs {
		title := c.Name
		if title == "" {
			title = "(untitled)"
		}
		for _, m := range c.Messages {
			text := m.Text
			if text == "" {
				var t []string
				for _, b := range m.Content {
					if b.Type == "text" {
						t = append(t, b.Text)
					}
				}
				text = strings.Join(t, "\n")
			}
			if strings.TrimSpace(text) == "" {
				continue
			}
			role := "user"
			if m.Sender == "assistant" {
				role = "assistant"
			}
			ts := parseTime(m.CreatedAt)
			if ts == 0 {
				ts = parseTime(c.CreatedAt)
			}
			out = append(out, unit{grp: f.path + "#" + c.UUID, source: "web", project: "claude.ai", session: c.UUID, title: mask(title), role: role, ts: ts, text: clip(mask(text), maxText)})
		}
	}
	return out, nil
}
