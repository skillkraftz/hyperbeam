// decisions: the project's design decisions are one file each in docs/decisions/ (front matter + Decision / Why / Rejected). This tool reads them.
//
//	decisions list [--topic T]   the implemented decisions, one line each
//	decisions check              front matter complete, references exist, superseded ones say what they collapsed into, no cycles
//	decisions index              print the generated index (docs/DECISIONS.md); feature PRs never regenerate it, the review pass does
//
// --dir DIR is the project folder (default: the current directory).
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type record struct {
	id, status, topic, title, code string
	prs, supersedes, collapsedInto []string
}

func main() {
	args := os.Args[1:]
	dir, topic := ".", ""
	var rest []string
	for i := 0; i < len(args); i++ {
		switch {
		case args[i] == "--dir" && i+1 < len(args):
			dir = args[i+1]
			i++
		case args[i] == "--topic" && i+1 < len(args):
			topic = args[i+1]
			i++
		default:
			rest = append(rest, args[i])
		}
	}
	if len(rest) == 0 || rest[0] == "-h" || rest[0] == "--help" || rest[0] == "help" {
		fmt.Println("usage: decisions [--dir DIR] list [--topic T] | check | index   (records: docs/decisions/*.md)")
		return
	}
	if rest[0] == "--version" {
		fmt.Println("decisions 1")
		return
	}
	recs, errs := load(filepath.Join(dir, "docs", "decisions"))
	switch rest[0] {
	case "list":
		for _, r := range recs {
			if r.status == "implemented" && (topic == "" || r.topic == topic) {
				fmt.Printf("%s  [%s]  %s\n", r.id, r.topic, r.title)
			}
		}
	case "check":
		errs = append(errs, check(recs)...)
		for _, e := range errs {
			fmt.Println("FAIL " + e)
		}
		if len(errs) > 0 {
			os.Exit(1)
		}
		fmt.Printf("ok: %d decisions\n", len(recs))
	case "index":
		fmt.Print(index(recs))
	default:
		fmt.Fprintln(os.Stderr, "decisions: unknown command "+rest[0])
		os.Exit(2)
	}
}

// load reads every *.md record, oldest first by id. Problems in a file are returned, not fatal.
func load(dir string) ([]record, []string) {
	files, _ := filepath.Glob(filepath.Join(dir, "*.md"))
	sort.Strings(files)
	var recs []record
	var errs []string
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			errs = append(errs, f+": "+err.Error())
			continue
		}
		r, err := parse(string(b))
		name := strings.TrimSuffix(filepath.Base(f), ".md")
		if err != nil {
			errs = append(errs, name+": "+err.Error())
			continue
		}
		if r.id != name {
			errs = append(errs, name+": id is "+r.id+", it must be the file name")
		}
		recs = append(recs, r)
	}
	return recs, errs
}

func parse(s string) (record, error) {
	var r record
	lines := strings.Split(s, "\n")
	if len(lines) < 2 || strings.TrimSpace(lines[0]) != "---" {
		return r, fmt.Errorf("no front matter (the file must start with ---)")
	}
	i := 1
	for ; i < len(lines) && strings.TrimSpace(lines[i]) != "---"; i++ {
		k, v, ok := strings.Cut(lines[i], ":")
		if !ok {
			continue
		}
		k, v = strings.TrimSpace(k), strings.TrimSpace(v)
		switch k {
		case "id":
			r.id = v
		case "status":
			r.status = v
		case "topic":
			r.topic = v
		case "code":
			r.code = v
		case "prs":
			r.prs = list(v)
		case "supersedes":
			r.supersedes = list(v)
		case "collapsed_into":
			r.collapsedInto = list(v)
		}
	}
	if i >= len(lines) {
		return r, fmt.Errorf("front matter is not closed with ---")
	}
	for _, l := range lines[i+1:] {
		if strings.HasPrefix(l, "# ") {
			r.title = strings.TrimSpace(l[2:])
			break
		}
	}
	return r, nil
}

// list reads "[a, b]" (or "a, b", or "a") into a slice.
func list(v string) []string {
	v = strings.Trim(strings.TrimSpace(v), "[]")
	var out []string
	for _, p := range strings.Split(v, ",") {
		if p = strings.TrimSpace(p); p != "" {
			out = append(out, p)
		}
	}
	return out
}

func check(recs []record) []string {
	var errs []string
	byID := map[string]record{}
	for _, r := range recs {
		byID[r.id] = r
	}
	for _, r := range recs {
		if r.status != "implemented" && r.status != "superseded" {
			errs = append(errs, r.id+": status must be implemented or superseded, not \""+r.status+"\"")
		}
		if r.topic == "" {
			errs = append(errs, r.id+": topic is missing")
		}
		if r.title == "" {
			errs = append(errs, r.id+": no # title line")
		}
		if r.status == "superseded" && len(r.collapsedInto) == 0 && r.code == "" {
			errs = append(errs, r.id+": superseded, but it does not say what it collapsed into (collapsed_into: or code:)")
		}
		if r.status == "implemented" && (len(r.collapsedInto) > 0) {
			errs = append(errs, r.id+": implemented, but has collapsed_into (set status: superseded)")
		}
		for _, t := range r.collapsedInto {
			if _, ok := byID[t]; !ok {
				errs = append(errs, r.id+": collapsed_into "+t+" does not exist")
			} else if t == r.id {
				errs = append(errs, r.id+": collapsed into itself")
			}
		}
		for _, t := range r.supersedes {
			o, ok := byID[t]
			if !ok {
				errs = append(errs, r.id+": supersedes "+t+" which does not exist")
			} else if o.status != "superseded" {
				errs = append(errs, r.id+": supersedes "+t+", but that one is still "+o.status+" (mark it superseded with collapsed_into)")
			}
		}
	}
	for _, r := range recs { // a cycle in collapsed_into
		seen := map[string]bool{}
		var walk func(id string) bool
		walk = func(id string) bool {
			if seen[id] {
				return id == r.id
			}
			seen[id] = true
			for _, n := range byID[id].collapsedInto {
				if n == r.id || walk(n) {
					return true
				}
			}
			return false
		}
		if walk(r.id) {
			errs = append(errs, r.id+": collapsed_into leads back to itself (a cycle)")
		}
	}
	return errs
}

func date(id string) string {
	if len(id) >= 10 {
		return id[:10]
	}
	return ""
}

func prs(r record) string {
	if len(r.prs) == 0 {
		return ""
	}
	return ", PR #" + strings.Join(r.prs, ", #")
}

func index(recs []record) string {
	var b strings.Builder
	b.WriteString("# Design decisions\n\nGenerated by `hyperbeam tool decisions index` from the records in `docs/decisions/`; never edit this file by hand (feature PRs add a record, the review pass regenerates this).\n")
	topics := map[string][]record{}
	var names []string
	for _, r := range recs {
		if r.status == "implemented" {
			if _, ok := topics[r.topic]; !ok {
				names = append(names, r.topic)
			}
			topics[r.topic] = append(topics[r.topic], r)
		}
	}
	sort.Strings(names)
	for _, t := range names {
		fmt.Fprintf(&b, "\n## %s\n", t)
		rs := topics[t]
		sort.Slice(rs, func(i, j int) bool { return rs[i].id > rs[j].id })
		for _, r := range rs {
			fmt.Fprintf(&b, "- [%s](decisions/%s.md) (%s%s)\n", r.title, r.id, date(r.id), prs(r))
		}
	}
	title := map[string]string{}
	for _, r := range recs {
		title[r.id] = r.title
	}
	var sup []record
	for _, r := range recs {
		if r.status == "superseded" {
			sup = append(sup, r)
		}
	}
	if len(sup) > 0 {
		b.WriteString("\n## Superseded\n")
		sort.Slice(sup, func(i, j int) bool { return sup[i].id > sup[j].id })
		for _, r := range sup {
			var into []string
			for _, t := range r.collapsedInto {
				into = append(into, fmt.Sprintf("[%s](decisions/%s.md)", title[t], t))
			}
			if r.code != "" {
				into = append(into, "`"+r.code+"`")
			}
			fmt.Fprintf(&b, "- ~~[%s](decisions/%s.md)~~ (%s%s) collapsed into %s\n", r.title, r.id, date(r.id), prs(r), strings.Join(into, ", "))
		}
	}
	return b.String()
}
