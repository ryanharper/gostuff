func createTempFile() (string, error) {
	// The first argument "" means to create the file in the default location.
	// The second argument "example-*.txt" is the pattern for the filename.
	// The "*" will be replaced with a random string.
	tempFile, err := os.CreateTemp("", "example-*.txt")
	if err != nil {
		return "", fmt.Errorf("could not create temp file: %w", err)
	}

	// It's good practice to close the file handle, though in this specific
	// function we only need the path.
	if err := tempFile.Close(); err != nil {
		return "", fmt.Errorf("could not close temp file: %w", err)
	}

	// Return the full path of the created file.
	return tempFile.Name(), nil
}

func main() {
	filePath, err := createTempFile()
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("Temporary file created at: %s\n", filePath)

	// It's important to clean up the temporary file when you're done with it.
	// We'll remove it here for demonstration.
	defer os.Remove(filePath)
}
