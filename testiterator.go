func iterateAnything(data any) {
	// Use a type switch to determine the concrete type of 'data'
	switch v := data.(type) {

	// Case 1: Check if it's a slice of strings
	case []string:
		fmt.Println("Iterating over a slice of strings:")
		for index, item := range v {
			fmt.Printf("  Index %d: %s\n", index, item)
		}

	// Case 2: Check if it's a map with string keys and int values
	case map[string]int:
		fmt.Println("Iterating over a map[string]int:")
		for key, value := range v {
			fmt.Printf("  Key '%s': %d\n", key, value)
		}

	// Default case: Handle all other types
	default:
		fmt.Printf("Cannot iterate over type %T\n", v)
	}
}

func main() {
	// Example with a slice
	sliceData := []string{"apple", "banana", "cherry"}
	iterateAnything(sliceData)

	fmt.Println("---")

	// Example with a map
	mapData := map[string]int{"one": 1, "two": 2}
	iterateAnything(mapData)

	fmt.Println("---")

	// Example with a non-iterable type
	intData := 123
	iterateAnything(intData)
}
