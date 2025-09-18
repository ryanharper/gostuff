package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/client"
)

// tagImage applies a new tag to a local Docker image.
// sourceImage is the original name (e.g., "hello-world:latest").
// newTag is the full new tag (e.g., "myregistry/myuser/hello-world:v1").
func tagImage(sourceImage, newTag string) error {
	ctx := context.Background()

	// 1. Create a new Docker client
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		return fmt.Errorf("could not create docker client: %w", err)
	}
	defer cli.Close()

	// 2. Tag the image
	log.Printf("Tagging image %s as %s...\n", sourceImage, newTag)
	err = cli.ImageTag(ctx, sourceImage, newTag)
	if err != nil {
		return fmt.Errorf("could not tag image: %w", err)
	}

	log.Printf("Successfully tagged image.")
	return nil
}

// pushImage pushes a tagged image to a Docker registry.
// imageToPush is the full name of the image to push (e.g., "myregistry/myuser/hello-world:v1").
// username and password are for authenticating with the registry.
func pushImage(imageToPush, username, password string) error {
	ctx := context.Background()

	// 1. Create a new Docker client
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		return fmt.Errorf("could not create docker client: %w", err)
	}
	defer cli.Close()

	// 2. Create authentication credentials
	authConfig := types.AuthConfig{
		Username: username,
		Password: password,
	}
	authConfigBytes, _ := json.Marshal(authConfig)
	authConfigEncoded := base64.URLEncoding.EncodeToString(authConfigBytes)

	pushOptions := types.ImagePushOptions{
		RegistryAuth: authConfigEncoded,
	}

	// 3. Push the image
	log.Printf("Pushing image %s...\n", imageToPush)
	pushResponse, err := cli.ImagePush(ctx, imageToPush, pushOptions)
	if err != nil {
		return fmt.Errorf("could not push image: %w", err)
	}
	defer pushResponse.Close()

	// 4. Print the response from the Docker daemon
	// This shows the push progress.
	_, err = io.Copy(os.Stdout, pushResponse)
	if err != nil {
		return fmt.Errorf("error reading push response: %w", err)
	}
	
	log.Printf("\nSuccessfully pushed image %s.", imageToPush)
	return nil
}

func main() {
	// --- Example Usage ---
	
	// Ensure you have "hello-world:latest" locally
	// You can get it by running: docker pull hello-world:latest
	sourceImage := "hello-world:latest"
	
	// Replace with your Docker Hub username or registry details
	dockerUsername := "your-dockerhub-username"
	newImageTag := fmt.Sprintf("%s/hello-world-tagged:v1", dockerUsername)

	// Step 1: Tag the local image
	err := tagImage(sourceImage, newImageTag)
	if err != nil {
		log.Fatalf("Tagging failed: %v", err)
	}

	fmt.Println("---")

	// Step 2: Push the newly tagged image
	// It's recommended to get credentials from a secure source like env variables.
	dockerPassword := "your-dockerhub-password" // or a Personal Access Token
	
	if dockerUsername == "your-dockerhub-username" || dockerPassword == "your-dockerhub-password" {
		log.Println("Skipping push: Please replace placeholder credentials in the main() function.")
		return
	}
	
	err = pushImage(newImageTag, dockerUsername, dockerPassword)
	if err != nil {
		log.Fatalf("Pushing failed: %v", err)
	}
}
