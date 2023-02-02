package main

import (
	"net/http"
	"net/url"

	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

const AuthHeader = "X-Racetrack-Auth"

var unprotectedEndpoints = []string{
	"/health",
	"/live",
	"/ready",
}

// Indicates legitimate failure of authentication (ie. wrong username or password), not technical error
type AuthenticationFailure struct {
	error
}

func (e AuthenticationFailure) Error() string {
	if e.error == nil {
		return "authentication failure"
	}
	return e.error.Error()
}

func AuthFailure(err error, msg string, debug bool) error {
	if debug {
		if err == nil {
			return AuthenticationFailure{errors.New(msg)}
		} else {
			return AuthenticationFailure{errors.Wrap(err, msg)}
		}
	} else {
		return AuthenticationFailure{errors.New("authentication failed")}
	}
}

func getAuthFromHeaderOrCookie(req *http.Request) string {
	authToken := readRequestIdentity(req, AuthHeader)
	if authToken != "" {
		return authToken
	}

	// TODO: abandon backward compatibility with old headers
	authToken = readRequestIdentity(req, "X-Racetrack-Esc-Auth")
	if authToken != "" {
		return authToken
	}
	authToken = readRequestIdentity(req, "X-Racetrack-Job-Auth")
	if authToken != "" {
		return authToken
	}
	authToken = readRequestIdentity(req, "X-Racetrack-User-Auth")
	if authToken != "" {
		return authToken
	}

	return ""
}

func readRequestIdentity(req *http.Request, headerName string) string {
	identityId := req.Header.Get(headerName)
	if identityId != "" {
		return identityId
	}

	identityCookie, err := req.Cookie(headerName)
	if err != nil {
		return ""
	}

	val := UnescapeCookie(identityCookie.Value)
	return val
}

func UnescapeCookie(value string) string {
	// needed because Lifecycle does escape cookie value to prevent double quoting
	decodedValue, err := url.QueryUnescape(value)
	if err != nil {
		log.Error("error un-escaping cookie value ", "value", value)
		return ""
	}
	return decodedValue
}
