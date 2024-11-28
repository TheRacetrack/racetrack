package main

import (
	"fmt"
)

// Wrap error with additional context message
func WrapError(message string, err error) error {
	return fmt.Errorf("%s: %w", message, err)
}
