package main

import (
        "context"
        "fmt"

        secretmanager "cloud.google.com/go/secretmanager/apiv1"
        "cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"
        "sigs.k8s.io/kustomize/api/resmap"
        "sigs.k8s.io/kustomize/api/resource"
        "sigs.k8s.io/kustomize/api/types"
        "sigs.k8s.io/yaml"
)

type plugin struct {
        rf          *resmap.Factory
        types.ObjectMeta `json:"metadata,omitempty" yaml:"metadata,omitempty"`
        Spec        struct {
                SecretName     string            `json:"secretName,omitempty" yaml:"secretName,omitempty"`
                SecretMappings map[string]string `json:"secretMappings,omitempty" yaml:"secretMappings,omitempty"`
        } `json:"spec,omitempty" yaml:"spec,omitempty"`
}

//nolint: go-lint
var KustomizePlugin plugin

func (p *plugin) Config(
        _ *resmap.PluginHelpers, c []byte) (err error) {
        p.Spec.SecretName = ""
        p.Spec.SecretMappings = nil
        return yaml.Unmarshal(c, p)
}

func (p *plugin) Generate() (resmap.ResMap, error) {
        ctx := context.Background()
        client, err := secretmanager.NewClient(ctx)
        if err != nil {
                return nil, fmt.Errorf("failed to create secretmanager client: %v", err)
        }
        defer client.Close()

        secretData := make(map[string]string)
        for secretKey, gsmSecretName := range p.Spec.SecretMappings {
                secretValue, err := fetchSecretFromGSM(ctx, client, gsmSecretName)
                if err != nil {
                        return nil, err
                }
                secretData[secretKey] = secretValue
        }

        // Create the Kubernetes Secret using the helper functions
        secret := &resource.Resource{
                RNode: *yaml.NewRNode(&yaml.Node{
                        Kind: yaml.MappingNode,
                        Tag:  "!!map",
                }),
        }
        secret.SetApiVersion("v1")
        secret.SetKind("Secret")
        secret.SetName(p.Spec.SecretName)
        secret.SetNamespace(p.ObjectMeta.Namespace)

        // Add the secret data
        err = secret.PipeE(
                yaml.SetField("type", yaml.NewStringRNode("Opaque")),
                yaml.SetField("data", yaml.NewMapRNode(&secretData)),
        )
        if err != nil {
                return nil, err
        }

        // Add an annotation to indicate that this secret was generated from GSM
        if err := secret.SetAnnotation("secret-source", "google-secret-manager"); err != nil {
                return nil, err
        }

        // Add the secret to the resource map
        rm := resmap.New()
        err = rm.Append(secret)
        if err != nil {
                return nil, err
        }

        return rm, nil
}

func fetchSecretFromGSM(ctx context.Context, client *secretmanager.Client, gsmSecretName string) (string, error) {
        // Assuming "latest" version for simplicity; you can add version management
        accessRequest := &secretmanagerpb.AccessSecretVersionRequest{
                Name: gsmSecretName + "/versions/latest",
        }

        result, err := client.AccessSecretVersion(ctx, accessRequest)
        if err != nil {
                return "", fmt.Errorf("failed to access secret version: %v", err)
        }

        return string(result.Payload.Data), nil
}

func main() {
}
