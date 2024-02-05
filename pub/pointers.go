package main

func ptr[T any](x T) *T {
	return &x
}
