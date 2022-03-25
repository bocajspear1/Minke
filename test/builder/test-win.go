package main

import (
    "log"
    "os/exec"
)

func main() {
	cmd := exec.Command("C:\\Windows\\system32\\notepad.exe")

    err := cmd.Run()

    if err != nil {
        log.Fatal(err)
    }
}