package main

import (
	"encoding/json"
	"net/http"

	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

func main() {
	log.Info("I wish only to serve...")
	mux := http.NewServeMux()
	mux.HandleFunc("/perform", performHandler)
	addr := ":7004"
	log.Info("Listening on HTTP address", log.Ctx{"addr": addr})
	err := http.ListenAndServe(addr, mux)
	if err != nil {
		panic(errors.Wrap(err, "Failed to serve"))
	}
}

func performHandler(w http.ResponseWriter, req *http.Request) {
	log.Debug("Perform request received")

	var input map[string]interface{}
	err := json.NewDecoder(req.Body).Decode(&input)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	output, err := perform(input)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(output)
}

func perform(input map[string]interface{}) (interface{}, error) {
	numbers, ok := input["numbers"]
	if !ok {
		return nil, errors.New("'numbers' parameter was not given")
	}
	numbersList := numbers.([]interface{})
	inputFloats := make([]float64, len(numbersList))
	var err error
	for i, arg := range numbersList {
		inputFloats[i] = arg.(float64)
		if err != nil {
			return nil, errors.Wrap(err, "converting argument to float64")
		}
	}

	var sum float64 = 0
	for _, number := range inputFloats {
		sum += number
	}

	return sum, nil
}
