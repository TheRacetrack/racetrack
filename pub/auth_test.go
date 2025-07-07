package main

import (
	"testing"

	"github.com/pkg/errors"
	"github.com/stretchr/testify/assert"
)

func TestCookieUnquoting(t *testing.T) {

	assert.Equal(t, "abcdefgh12346", UnescapeCookie("abcdefgh12346"))

	assert.Equal(t, "eyJ1c2VybmFtZSI6ICJhZG1tlbiI6ICJhYTkyOTI3Mi14OGMtOTJlNC1hNDNjNGFhYzFhMzQif/+=",
		UnescapeCookie("eyJ1c2VybmFtZSI6ICJhZG1tlbiI6ICJhYTkyOTI3Mi14OGMtOTJlNC1hNDNjNGFhYzFhMzQif%2F%2B%3D"))

}

func TestAuthenticationFailureError(t *testing.T) {
	err := AuthenticationFailure{errors.Wrap(errors.New("root cause"), "authentication failed")}
	assert.Error(t, err)
	assert.Equal(t, "authentication failed: root cause", err.Error())

	err = AuthenticationFailure{nil}
	assert.Error(t, err)
	assert.Equal(t, "authentication failure", err.Error())
}
