package main

import (
	"database/sql"
	_ "github.com/lib/pq"
)

func main() {
	db, _ := sql.Open("postgres", "postgres://localhost/test")
	_ = db
}
