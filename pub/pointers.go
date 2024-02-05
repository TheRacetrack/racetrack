package main

// Create a pointer to a value of any type (useful for filling optional fields inline)
func ptr[T any](x T) *T {
	return &x
}
