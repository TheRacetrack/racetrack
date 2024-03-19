package main

// Create a pointer to a value of any type (useful for filling optional fields inline)
func ptr[T any](x T) *T {
	return &x
}

// MapSlice applies a function to each element of a slice and returns a new slice with the results
func MapSlice[T any, R any](input []T, mapper func(T) R) []R {
	s2 := make([]R, len(input))
	for i, v := range input {
		s2[i] = mapper(v)
	}
	return s2
}

type Pair[T, U any] struct {
	First  T
	Second U
}

// one-line if-else statement
func IfThenElse[T any](condition bool, a T, b T) T {
	if condition {
		return a
	}
	return b
}
