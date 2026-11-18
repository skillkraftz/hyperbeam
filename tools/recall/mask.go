package main

import (
	"regexp"
	"strings"
)

// Secret masking: applied when indexing (so the database never holds them) and again when printing.
var (
	reKnown = regexp.MustCompile(`(?i)\b(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*)`)
	reKV    = regexp.MustCompile(`(?i)\b([A-Za-z0-9_]*(?:api[_-]?key|token|secret|passw(?:or)?d|private[_-]?key)[A-Za-z0-9_]*\s*[=:]\s*)["']?[^\s"',;]{6,}`)
	reBear  = regexp.MustCompile(`(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{16,}`)
	reLong  = regexp.MustCompile(`[A-Za-z0-9_+=-]{32,}`)
	reHex40 = regexp.MustCompile(`^[0-9a-f]{40}$`)
)

func mask(s string) string {
	if len(s) < 8 {
		return s
	}
	s = reKnown.ReplaceAllString(s, "[secret]")
	s = reBear.ReplaceAllString(s, "${1}[secret]")
	s = reKV.ReplaceAllString(s, "${1}[secret]")
	s = reLong.ReplaceAllStringFunc(s, func(m string) string {
		if reHex40.MatchString(m) || !strings.ContainsAny(m, "0123456789") || !strings.ContainsAny(strings.ToLower(m), "abcdefghijklmnopqrstuvwxyz") {
			return m
		}
		return "[secret]"
	})
	return s
}
