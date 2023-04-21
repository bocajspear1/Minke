package main

import (
    "log"
    "os/exec"
)

func main() {
	cmd := exec.Command("touch /tmp/hello")

    err := cmd.Run()

    if err != nil {
        log.Fatal(err)
    }
}