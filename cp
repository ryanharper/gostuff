package main

import (
    "context"
    "fmt"
    "io"
    "log"
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
        version, err := it.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            return fmt.Errorf("failed to list versions: %v", err)
        }
        if version.Name == fmt.Sprintf("%s/versions/%s", packageName, version) {
            packageVersion = version
            break
        }
    }

    if packageVersion == nil {
        return fmt.Errorf("version %s not found for package %s", version, packageName)
    }

    // Download the package version
    versionReq := &artifactregistrypb.GetVersionRequest{
        Name: packageVersion.Name,
    }
    versionResp, err := client.GetVersion(ctx, versionReq)
    if err != nil {
        return fmt.Errorf("failed to get package version: %v", err)
    }

    // Write the package content to the output file
    outputFile, err := os.Create(outputPath)
    if err != nil {
        return fmt.Errorf("failed to create output file: %v", err)
    }
    defer outputFile.Close()

    _, err = io.Copy(outputFile, versionResp.GetContent())
    if err != nil {
        return fmt.Errorf("failed to write package content to file: %v", err)
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
