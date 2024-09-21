package main

import (
    "fmt"
    "strings"
)

func isUppercase(s string) bool {
    return s == strings.ToUpper(s)
}

func main() {
    str1 := "HELLO WORLD"
    str2 := "Hello World"

    fmt.Println(isUppercase(str1)) // Output: true
    fmt.Println(isUppercase(str2)) // Output: false
}
