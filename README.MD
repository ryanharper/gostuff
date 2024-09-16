```
package main

import (
    "fmt"
    "os"
    "os/exec"
    "strings"

    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

type Target struct {
    Name      string            `mapstructure:"name"`
    Variables map[string]string `mapstructure:"variables"`
}

func main() {
    var configFile string
    var targetName string

    rootCmd := &cobra.Command{
        Use:   "skaffmate [target] [skaffold args...]",
        Short: "Skaffold wrapper with environment variable management",
        Args:  cobra.MinimumNArgs(1),
        Run: func(cmd *cobra.Command, args []string) {
            targetName = args[0]
            skaffoldArgs := args[1:]

            // Load configuration
            viper.SetConfigFile(configFile)
            viper.SetConfigType("yaml")
            if err := viper.ReadInConfig(); err != nil {
                fmt.Println("Error reading config file:", err)
                os.Exit(1)
            }

            // Find target
            var targets []Target
            if err := viper.UnmarshalKey("targets", &targets); err != nil {
                fmt.Println("Error unmarshaling targets:", err)
                os.Exit(1)
            }

            var selectedTarget *Target
            for _, t := range targets {
                if t.Name == targetName {
                    selectedTarget = &t
                    break
                }
            }

            if selectedTarget == nil {
                fmt.Println("Target not found:", targetName)
                os.Exit(1)
            }

            // Set environment variables
            for k, v := range selectedTarget.Variables {
                os.Setenv("GRAPH_"+k, v)
            }

            // Run skaffold with additional arguments
            runSkaffold(skaffoldArgs)
        },
    }

    rootCmd.Flags().StringVarP(&configFile, "config", "c", "skaffmate.yaml", "Configuration file path")

    if err := rootCmd.Execute(); err != nil {
        fmt.Println("Error:", err)
        os.Exit(1)
    }
}

func runSkaffold(args []string) {
    cmd := exec.Command("skaffold", args...)

    // Get pipes for stdout and stderr
    stdoutPipe, err := cmd.StdoutPipe()
    if err != nil {
        fmt.Println("Error creating stdout pipe:", err)
        os.Exit(1)
    }
    stderrPipe, err := cmd.StderrPipe()
    if err != nil {
        fmt.Println("Error creating stderr pipe:", err)
        os.Exit(1)
    }

    // Start the command
    if err := cmd.Start(); err != nil {
        fmt.Println("Error starting skaffold:", err)
        os.Exit(1)
    }

    // Handle Ctrl+C to kill Skaffold
    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt)
    go func() {
        <-c
        fmt.Println("\nInterrupt signal received, terminating Skaffold...")
        if err := cmd.Process.Kill(); err != nil {
            fmt.Println("Error killing Skaffold process:", err)
        }
    }()

    // Stream stdout and stderr
    go func() {
        scanner := bufio.NewScanner(stdoutPipe)
        for scanner.Scan() {
            fmt.Println(scanner.Text())
        }
    }()
    go func() {
        scanner := bufio.NewScanner(stderrPipe)
        for scanner.Scan() {
            fmt.Fprintln(os.Stderr, scanner.Text()) // Print to stderr
        }
    }()

    // Wait for the command to finish
    if err := cmd.Wait(); err != nil {
        if exitErr, ok := err.(*exec.ExitError); ok {
            os.Exit(exitErr.ExitCode()) // Propagate Skaffold's exit code
        } else {
            fmt.Println("Error waiting for skaffold:", err)
            os.Exit(1)
        }
    }
}

func runSkaffold2(args []string) {
    cmd := exec.Command("skaffold", args...)

    // Get pipes for stdout and stderr
    stdoutPipe, err := cmd.StdoutPipe()
    if err != nil {
        fmt.Println("Error creating stdout pipe:", err)
        os.Exit(1)
    }
    stderrPipe, err := cmd.StderrPipe()
    if err != nil {
        fmt.Println("Error creating stderr pipe:", err)
        os.Exit(1)
    }

    // Start the command
    if err := cmd.Start(); err != nil {
        fmt.Println("Error starting skaffold:", err)
        os.Exit(1)
    }

    // Handle Ctrl+C to kill Skaffold
    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt)
    go func() {
        <-c
        fmt.Println("\nInterrupt signal received, terminating Skaffold...")
        if err := cmd.Process.Kill(); err != nil {
            fmt.Println("Error killing Skaffold process:", err)
        }
    }()

    // Copy stdout and stderr directly to the console
    go io.Copy(os.Stdout, stdoutPipe)
    go io.Copy(os.Stderr, stderrPipe)

    // Wait for the command to finish
    if err := cmd.Wait(); err != nil {
        if exitErr, ok := err.(*exec.ExitError); ok {
            os.Exit(exitErr.ExitCode()) 
        } else {
            fmt.Println("Error waiting for skaffold:", err)
            os.Exit(1)
        }
    }
}
```
```
package main

import (
    "crypto/tls"
    "fmt"
    "io/ioutil"
    "log"
    "net/http"
    "net/http/httputil"
    "net/url"
    "os"
)

func main() {
    targetURL, err := url.Parse(os.Getenv("TARGET_URL"))
    if err != nil {
        log.Fatalf("Error parsing TARGET_URL: %v", err)
    }

    customHeaders := map[string]string{
        "X-Custom-Header-1": "Value1",
        "X-Custom-Header-2": "Value2",
        // Add more custom headers as needed
    }

    // TLS configuration (adjust as needed)
    tlsConfig := &tls.Config{
        // InsecureSkipVerify: true, // Use with caution! Only for testing or self-signed certs
        // RootCAs: ... // Provide root CAs if needed
        // ServerName: ... // Set if needed for SNI
    }

    // Configure transport for HTTPS
    transport := &http.Transport{TLSClientConfig: tlsConfig}

    proxy := httputil.NewSingleHostReverseProxy(targetURL)
    proxy.Transport = transport // Set the transport for HTTPS support
    proxy.Director = func(req *http.Request) {
        req.URL.Scheme = targetURL.Scheme
        req.URL.Host = targetURL.Host
        req.Host = targetURL.Host   


        for key, value := range customHeaders {
            req.Header.Set(key, value)
        }
    }

    proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
        log.Printf("Error proxying request: %v", err)
        // You might want to handle TLS errors more specifically here
        http.Error(w, "Internal Server Error", http.StatusInternalServerError)
    }

    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }
    fmt.Printf("Interception proxy listening on port %s...\n", port)
    log.Fatal(http.ListenAndServe(":"+port, proxy))
}
```

```
#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
if [ "${1#-}" != "$1" ]; then
	set -- memcached "$@"
fi

exec "$@"
```

dockerfile
```
FROM debian:bookworm-slim

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN set -eux; \
	groupadd --system --gid 11211 memcache; \
	useradd --system --gid memcache --uid 11211 memcache

# ensure SASL's "libplain.so" is installed as per https://github.com/memcached/memcached/wiki/SASLHowto
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		libsasl2-modules \
	; \
	rm -rf /var/lib/apt/lists/*

ENV MEMCACHED_VERSION 1.6.29
ENV MEMCACHED_URL https://memcached.org/files/memcached-1.6.29.tar.gz
ENV MEMCACHED_SHA1 a9699aed111d86b6e37b3ce5e6ef4e7539582d5f

RUN set -eux; \
	\
	savedAptMark="$(apt-mark showmanual)"; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		dpkg-dev \
		gcc \
		libc6-dev \
		libevent-dev \
		libio-socket-ssl-perl \
		libsasl2-dev \
		libssl-dev \
		make \
		perl \
		wget \
	; \
	rm -rf /var/lib/apt/lists/*; \
	\
	wget -O memcached.tar.gz "$MEMCACHED_URL"; \
	echo "$MEMCACHED_SHA1  memcached.tar.gz" | sha1sum -c -; \
	mkdir -p /usr/src/memcached; \
	tar -xzf memcached.tar.gz -C /usr/src/memcached --strip-components=1; \
	rm memcached.tar.gz; \
	\
	cd /usr/src/memcached; \
	\
	gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"; \
	./configure \
		--build="$gnuArch" \
		--enable-extstore \
		--enable-sasl \
		--enable-sasl-pwdb \
		--enable-tls \
	; \
	nproc="$(nproc)"; \
	make -j "$nproc"; \
	\
# see https://github.com/docker-library/memcached/pull/54#issuecomment-562797748 and https://bugs.debian.org/927461 for why we have to munge openssl.cnf
	sed -i.bak 's/SECLEVEL=2/SECLEVEL=1/g' /etc/ssl/openssl.cnf; \
	make test PARALLEL="$nproc"; \
	mv /etc/ssl/openssl.cnf.bak /etc/ssl/openssl.cnf; \
	\
	make install; \
	\
	cd /; \
	rm -rf /usr/src/memcached; \
	\
	apt-mark auto '.*' > /dev/null; \
	apt-mark manual $savedAptMark > /dev/null; \
	find /usr/local -type f -executable -exec ldd '{}' ';' \
		| awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); printf "*%s\n", so }' \
		| sort -u \
		| xargs -r dpkg-query --search \
		| cut -d: -f1 \
		| sort -u \
		| xargs -r apt-mark manual \
	; \
	apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
	\
	memcached -V

COPY docker-entrypoint.sh /usr/local/bin/
RUN ln -s usr/local/bin/docker-entrypoint.sh /entrypoint.sh # backwards compat
ENTRYPOINT ["docker-entrypoint.sh"]

USER memcache
EXPOSE 11211
CMD ["memcached"]
```

Sure, here is the expanded code with an additional function that iterates over the filtered repositories, retrieves all the GitHub topics associated with each repository, and stores them in a map with the repository name as the key and the latest tag associated with that repository as the value:

```
{
  "extends": [
    "config:base"
  ],
  "schedule": ["before 5am on Monday"],
  "packageRules": [
    {
      "matchDepTypes": ["golang"],
      "matchUpdateTypes": ["minor", "patch", "pin", "digest"]
    },
    {
      "matchPackageNames": ["github.com/stretchr/testify"],
      "matchUpdateTypes": ["major"] // Allow major updates for testify
    }
  ]
}

```


```
package test

import (
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/helm"
	"github.com/gruntwork-io/terratest/modules/k8s"
	"github.com/stretchr/testify/require"   

)

func TestOTelCollectorDeployment(t *testing.T) {
	t.Parallel()

	// Path to your Helm chart
	helmChartPath := "../path/to/your/otel-collector-chart"

	// Helm install options
	options := &helm.Options{
		SetValues: map[string]string{
			// Any configuration values for your chart
		},
	}

	// Install the Helm chart
	helm.Install(t, options, helmChartPath, "my-otel-collector")

	// Wait for the service to be up and running
	k8s.WaitUntilServiceAvailable(t, "my-otel-collector", 10, 1*time.Minute)

	// Optionally, you can add more assertions here to check specific aspects of the deployment

	// No teardown in this test, as requested
}
```

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

secretGenerator:
- name: my-secret
  envs:
  - secret.env # A file containing the Secret Manager reference
  options:
    disableNameSuffixHash: true
```

```
my-secret-key=sm://projects/[PROJECT_ID]/secrets/[SECRET_NAME]/versions/[VERSION]
```


```go
transform:
    logs:
      statements:
        - type: regex
          error_mode: ignore
          regex:
            field: attributes.message
            pattern: "(?i)(password|secret|token)=(\\S+)"
            replacement: "$1=***"


Bash
PUT /subscription_lookup  
{
  "mappings": {
    "properties": {
      "resource_id": { 
        "type": "keyword" 
      },
      "subscription_name": { 
        "type": "text" 
      }
    }
  }
}

{
  "mappings": {
    "properties": {
      "resource_id": { 
        "type": "keyword" 
      },
      "subscription_name": { 
        "type": "text" 
      }
    }
  }
}

PUT _ingest/pipeline/azure_subscription_enrich_pipeline
{
  "description": "Enriches Azure documents with subscription name",
  "processors": [
    {
      "enrich": {
        "policy_name": "azure_subscription_enrich_policy",
        "field": "azure_resource_id",
        "target_field": "subscription_name"
      }
    }
  ]
}









package githubfilter

import (
    "context"
    "fmt"
    "io/ioutil"
    "net/http"
    "regexp"
    "strings"

    "github.com/google/go-github/v47/github"
)

// FilterRepositories filters a list of repositories based on a regular expression.
func FilterRepositories(ctx context.Context, client *github.Client, regex string, repos []github.Repository) ([]github.Repository, error) {
    filteredRepos := []github.Repository{}

    re, err := regexp.Compile(regex)
    if err != nil {
        return nil, err
    }

    for _, repo := range repos {
        repoName := repo.GetFullName()
        if re.MatchString(repoName) {
            filteredRepos = append(filteredRepos, repo)
        }
    }

    return filteredRepos, nil
}

// GetLatestReleaseTag gets the latest release tag for a repository.
func GetLatestReleaseTag(ctx context.Context, client *github.Client, repo github.Repository) (string, error) {
    releases, _, err := client.Repositories.ListReleases(ctx, repo.GetOwner().GetLogin(), repo.GetName(), &github.ListOptions{PerPage: 1})
    if err != nil {
        return "", err
    }

    if len(releases) == 0 {
        return "", nil
    }

    latestRelease := releases[0]
    return latestRelease.GetTagName(), nil
}

// GetRepositoryTopics gets the GitHub topics associated with a repository.
func GetRepositoryTopics(ctx context.Context, client *github.Client, repo github.Repository) ([]string, error) {
    topics, _, err := client.Repositories.ListTopics(ctx, repo.GetOwner().GetLogin(), repo.GetName())
    if err != nil {
        return nil, err
    }

    topicNames := []string{}
    for _, topic := range topics {
        topicNames = append(topicNames, topic.GetName())
    }

    return topicNames, nil
}

// FilterAndGetRepositoryTopicsAndLatestReleaseTags filters a list of repositories based on a regular expression, retrieves all the GitHub topics associated with each repository, and stores them in a map with the repository name as the key and the latest tag associated with that repository as the value.
func FilterAndGetRepositoryTopicsAndLatestReleaseTags(ctx context.Context, client *github.Client, regex string, repos []github.Repository) (map[string]string, error) {
    filteredRepos, err := FilterRepositories(ctx, client, regex, repos)
    if err != nil {
        return nil, err
    }

    repositoryTopicsMap := make(map[string]string)
    for _, repo := range filteredRepos {
        latestReleaseTag, err := GetLatestReleaseTag(ctx, client, repo)
        if err != nil {
            return nil, err
        }

        repositoryTopics, err := GetRepositoryTopics(ctx, client, repo)
        if err != nil {
            return nil, err
        }

        repositoryTopicsMap[repo.GetFullName()] = latestReleaseTag + " [" + strings.Join(repositoryTopics, ", ") + "]"
    }

    return repositoryTopicsMap, nil
}
```

To use this expanded code, you can call the `FilterAndGetRepositoryTopicsAndLatestReleaseTags` function to retrieve the repository topics and latest release tags for the filtered repositories:

```go
ctx := context.Background()
client := github.NewClient(&http.Client{})

repos, _, err := client.Repositories.List(ctx, "my-org", &github.ListOptions{PerPage: 100})
if err != nil {
    fmt.Println(err)
    return
}

repositoryTopicsMap, err := githubfilter.FilterAndGetRepositoryTopicsAndLatestReleaseTags(ctx, client, `"my-org/.*"`, repos)
if err != nil {
    fmt.Println(err)
    return
}

for repoName, topicsAndTag := range repositoryTopicsMap {
    fmt.Println(repoName, ":", topicsAndTag)
}


### Submit file


```

// SubmitJSONToGitHubRepository submits the generated JSON file to another GitHub repository.
func SubmitJSONToGitHubRepository(ctx context.Context, client *github.Client, repositoryName string, owner string, branch string, filePath string) error {
    jsonBytes, err := json.Marshal(repositoryTopicsMap)
    if err != nil {
        return err
    }

    jsonFile, err := ioutil.TempFile("", "repositoryTopicsMap.json")
    if err != nil {
        return err
    }

    defer jsonFile.Close()

    _, err = jsonFile.Write(jsonBytes)
    if err != nil {
        return err
    }

    _, _, err := client.Repositories.CreateFile(ctx, owner, repositoryName, jsonFile.
```

```
// CheckForDifferences checks for differences between local and remote JSON files. It returns a boolean indicating whether there are any differences and a map of any differences found.
func CheckForDifferences(ctx context.Context, client *github.Client, filePath string, owner string, repositoryName string, branch string) (bool, map[string]string, error) {
    localJSONMap, err := LoadJSONFromFile(filePath)
    if err != nil {
        return false, nil, err
    }

    remoteFileContent, _, _, err := client.Repositories.GetContents(ctx, owner, repositoryName, filePath, &github.RepositoryContentOptions{Ref: branch})
    if err != nil {
        if err == github.NotFound {
            // Remote file does not exist, so there are differences
            return true, localJSONMap, nil
        }
        return false, nil, err
    }

    remoteJSONString := string(remoteFileContent.GetContent())
    var remoteJSONMap map[string]string
    err = json.Unmarshal([]byte(remoteJSONString), &remoteJSONMap)
    if err != nil {
        return false, nil, err
    }

    differences := make(map[string]string)
    for key, localValue := range localJSONMap {
        remoteValue, ok := remoteJSONMap[key]
        if !ok || localValue != remoteValue {
            differences[key] = localValue
        }
    }

    return len(differences) > 0, differences, nil
}
```

#### GO FUNCTION FOR ORG POLICIES

```go
package main

import (
	"context"
	"fmt"

	cloudresourcemanager "cloud.google.com/go/resourcemanager/apiv3"
	"google.golang.org/api/option"
	crmv1 "google.golang.org/api/cloudresourcemanager/v1"
)

func getProjectOrganization(projectID string) (string, error) {
	ctx := context.Background()

	// Create a CRM client using the appropriate method
	crmService, err := crmv1.NewService(ctx, option.WithCredentialsFile("path/to/credentials.json"))
	if err != nil {
		return "", fmt.Errorf("creating cloudresourcemanager client: %w", err)
	}

	project, err := crmService.Projects.GetAncestry(projectID).Do()
	if err != nil {
		return "", fmt.Errorf("getting project ancestry: %w", err)
	}

	// The organization ID is in the parent chain of the project.
	for _, parentNode := range project.Ancestor {
		if parentNode.Type == "ORGANIZATION" {
			return parentNode.ResourceId.Id(), nil
		}
	}

	// If no organization is found, return an error.
	return "", fmt.Errorf("project %s is not part of an organization", projectID)
}

func main() {
	projectID := "your-project-id"
	organizationID, err := getProjectOrganization(projectID)
	if err != nil {
		fmt.Println(err)
	} else {
		fmt.Println("Project organization:", organizationID)
	}
}
```

another one 

```go

package main

import (
    "context"
    "fmt"
    "log"

    orgpolicy "cloud.google.com/go/orgpolicy/apiv1"
    "google.golang.org/api/iterator"
)

func listOrganizationPolicies(projectID string) ([]*orgpolicy.Policy, error) {
    ctx := context.Background()
    client, err := orgpolicy.NewClient(ctx)
    if err != nil {
        return nil, fmt.Errorf("orgpolicy.NewClient: %v", err)
    }

    defer client.Close()

    req := &orgpolicy.ListPoliciesRequest{
        Parent: fmt.Sprintf("projects/%s", projectID),
    }

    // Iterate through policies returned by the API
    policies := []*orgpolicy.Policy{}
    it := client.ListPolicies(ctx, req)
    for {
        policy, err := it.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            return nil, fmt.Errorf("ListPolicies: %v", err)
        }
        policies = append(policies, policy)
    }

    return policies, nil
}

func main() {
    projectID := "your-project-id"  // Replace with your actual project ID

    policies, err := listOrganizationPolicies(projectID)
    if err != nil {
        log.Fatal(err)
    }

    for _, policy := range policies {
        fmt.Printf("Policy: %s\n", policy.Name)
        fmt.Printf("  Constraints: %v\n", policy.Spec)
        fmt.package main

import (
    "context"
    "fmt"
    "log"

    orgpolicy "cloud.google.com/go/orgpolicy/apiv1"
    "google.golang.org/api/iterator"
)

func listOrganizationPolicies(projectID string) ([]*orgpolicy.Policy, error) {
    ctx := context.Background()
    client, err := orgpolicy.NewClient(ctx)
    if err != nil {
        return nil, fmt.Errorf("orgpolicy.NewClient: %v", err)
    }

    defer client.Close()

    req := &orgpolicy.ListPoliciesRequest{
        Parent: fmt.Sprintf("projects/%s", projectID),
    }

    // Iterate through policies returned by the API
    policies := []*orgpolicy.Policy{}
    it := client.ListPolicies(ctx, req)
    for {
        policy, err := it.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            return nil, fmt.Errorf("ListPolicies: %v", err)
        }
        policies = append(policies, policy)
    }

    return policies, nil
}

func main() {
    projectID := "your-project-id"  // Replace with your actual project ID

    policies, err := listOrganizationPolicies(projectID)
    if err != nil {
        log.Fatal(err)
    }

    for _, policy := range policies {
        fmt.Printf("Policy: %s\n", policy.Name)
        fmt.Printf("  Constraints: %v\n", policy.Spec)
        fmt.package main

import (
    "context"
    "fmt"
    "log"

    "cloud.google.com/go/resourcemanager/apiv3"
)

func listOrganizationPolicies(projectID string) ([]*resourcemanager.OrgPolicy, error) {
    ctx := context.Background()

    // Create a client for the Cloud Resource Manager API
    client, err := resourcemanager.NewProjectsClient(ctx)
    if err != nil {
        return nil, fmt.Errorf("resourcemanager.NewProjectsClient: %v", err)
    }
    defer client.Close()

    // Get the parent resource for organization policies
    parentResource := fmt.Sprintf("projects/%s", projectID)

    // Iterate through all available constraints to retrieve policies
    policies := []*resourcemanager.OrgPolicy{}
    constraints := []string{
        "constraints/compute.trustedImageProjects", // Example constraint
        // Add other constraints as needed
    }

    for _, constraint := range constraints {
        req := &resourcemanager.GetOrgPolicyRequest{
            Constraint: constraint,
            Resource:   parentResource,
        }

        policy, err := client.GetOrgPolicy(ctx, req)
        if err != nil {
            return nil, fmt.Errorf("GetOrgPolicy: %v", err)
        }
        policies = append(policies, policy)
    }

    return policies, nil
}

func main() {
    projectID := "your-project-id"  // Replace with your actual project ID

    policies, err := listOrganizationPolicies(projectID)
    if err != nil {
        log.Fatal(err)
    }

    for _, policy := range policies {
        fmt.Printf("Policy: %s\n", policy.Name)
        fmt.Printf("  Constraints: %v\n", policy.Spec)
        fmt.package main

import (
    "context"
    "fmt"
    "log"

    "cloud.google.com/go/compute/apiv1"
)

func listDisks(projectID string) ([]*compute.Disk, error) {
    ctx := context.Background()
    client, err := compute.NewDisksClient(ctx)
    if err != nil {
        return nil, fmt.Errorf("compute.NewDisksClient: %v", err)
    }
    defer client.Close()

    req := &compute.DiskListRequest{
        Project: projectID,
    }

    it := client.List(ctx, req)
    allDisks := []*compute.Disk{}
    for {
        resp, err := it.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            return nil, fmt.Errorf("List: %v", err)
        }
        allDisks = append(allDisks, resp)
    }

    return allDisks, nil
}

func main() {
    projectID := "your-project-id"  // Replace with your actual project ID

    disks, err := listDisks(projectID)
    if err != nil {
        log.Fatal(err)
    }

    for _, disk := range disks {
        fmt.Printf("Disk: %s\n", disk.Name)
        fmt.Printf("  Zone: %s\n", disk.Zone)
        fmt.Printf("  Size: %d GB\n", disk.SizeGb)
        fmt.Println()
    }
}







```
