package main

import (
    "context"
    "fmt"
    "io"
    "log"
    "net/http"
    "os"

    "cloud.google.com/go/artifactregistry/apiv1"
    artifactregistrypb "google.golang.org/genproto/googleapis/devtools/artifactregistry/v1"
    "google.golang.org/api/iterator"
)

func downloadPackageVersion(projectID, location, repository, packageName, version, outputPath string) error {
    ctx := context.Background()

    // Initialize the Artifact Registry client
    client, err := artifactregistry.NewClient(ctx)
    if err != nil {
        return fmt.Errorf("failed to create artifact registry client: %v", err)
    }
    defer client.Close()

    // Construct the package name
    packageName = fmt.Sprintf("projects/%s/locations/%s/repositories/%s/packages/%s", projectID, location, repository, packageName)

    // List the versions of the package
    req := &artifactregistrypb.ListVersionsRequest{
        Parent: packageName,
    }
    it := client.ListVersions(ctx, req)

    var packageVersion *artifactregistrypb.Version
    for {
        v, err := it.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            return fmt.Errorf("failed to list versions: %v", err)
        }
        if v.Name == fmt.Sprintf("%s/versions/%s", packageName, version) {
            packageVersion = v
            break
        }
    }

    if packageVersion == nil {
        return fmt.Errorf("version %s not found for package %s", version, packageName)
    }

    // Get the download URL for the package version
    // Note: This part depends on the type of artifact and how it's stored in the registry.
    // For example, if it's a Docker image, you would use a different method.
    // Here, we assume it's a generic file stored in the registry.

    // Construct the file name
    fileName := fmt.Sprintf("%s-%s", packageName, version)

    // Download the file using HTTP GET request
    resp, err := http.Get(fileName)
    if err != nil {
        return fmt.Errorf("failed to download file: %v", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return fmt.Errorf("failed to download file: received status code %d", resp.StatusCode)
    }

    // Write the file content to the output file
    outputFile, err := os.Create(outputPath)
    if err != nil {
        return fmt.Errorf("failed to create output file: %v", err)
    }
    defer outputFile.Close()

    _, err = io.Copy(outputFile, resp.Body)
    if err != nil {
        return fmt.Errorf("failed to write file content to output file: %v", err)
    }

    return nil
}

func main() {
    projectID := "your-project-id"
    location := "your-location"
    repository := "your-repository"
    packageName := "your-package-name"
    version := "your-package-version"
    outputPath := "path/to/output/file"

    err := downloadPackageVersion(projectID, location, repository, packageName, version, outputPath)
    if err != nil {
        log.Fatalf("Failed to download package version: %v", err)
    }

    fmt.Println("Package version downloaded successfully")
}
