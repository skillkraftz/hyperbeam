// test-timing: run shell commands one after another and print, for each, the wall time, the average number of cores it kept busy
// (CPU time of the command and everything it waited for, divided by wall time) and its exit code. Shows at a glance whether a test
// suite uses the machine: compare a 1-worker run with the default, e.g.
//
//	hyperbeam tool test-timing "npx vitest run --maxWorkers=1" "npx vitest run"
package main

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"syscall"
	"time"
)

func main() {
	args := os.Args[1:]
	if len(args) == 0 || args[0] == "-h" || args[0] == "--help" || args[0] == "help" {
		fmt.Println(`usage: test-timing "COMMAND" ["COMMAND"...]
Runs each command with sh -c (output hidden, its last lines shown on failure) and prints: wall time, average cores busy, exit code.
Example: hyperbeam tool test-timing "npx vitest run --maxWorkers=1" "npx vitest run"`)
		return
	}
	if args[0] == "--version" {
		fmt.Println("test-timing 1")
		return
	}
	fmt.Printf("machine: %d cores\n", runtime.NumCPU())
	worst := 0
	for _, c := range args {
		cmd := exec.Command("sh", "-c", c)
		var out tail
		cmd.Stdout, cmd.Stderr = &out, &out
		start := time.Now()
		err := cmd.Run()
		wall := time.Since(start).Seconds()
		code := 0
		if err != nil {
			code = 1
			if ee, ok := err.(*exec.ExitError); ok && ee.ExitCode() > 0 {
				code = ee.ExitCode()
			}
		}
		cores := 0.0
		if ps := cmd.ProcessState; ps != nil && wall > 0 {
			if ru, ok := ps.SysUsage().(*syscall.Rusage); ok {
				cpu := float64(ru.Utime.Sec+ru.Stime.Sec) + float64(ru.Utime.Usec+ru.Stime.Usec)/1e6
				cores = cpu / wall
			}
		}
		fmt.Printf("%8.1f s  %5.1f cores  exit %-3d %s\n", wall, cores, code, c)
		if code != 0 {
			fmt.Print(out.last(8))
			worst = code
		}
	}
	os.Exit(worst)
}

// tail keeps the last 64 KB of output.
type tail struct{ b []byte }

func (t *tail) Write(p []byte) (int, error) {
	t.b = append(t.b, p...)
	if len(t.b) > 65536 {
		t.b = t.b[len(t.b)-65536:]
	}
	return len(p), nil
}

func (t *tail) last(n int) string {
	s := string(t.b)
	for i, k := len(s)-1, 0; i >= 0; i-- {
		if s[i] == '\n' && i != len(s)-1 {
			if k++; k == n {
				return s[i+1:]
			}
		}
	}
	return s
}
