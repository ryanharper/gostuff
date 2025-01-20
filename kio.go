package main

import (
        "context"
        "fmt"
        "os"

        secretmanager "cloud.google.com/go/secretmanager/apiv1"
        "cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"
        "sigs.k8s.io/kustomize/kyaml/fn/framework"
        "sigs.k8s.io/kustomize/kyaml/fn/framework/command"
        "sigs.k8s.io/kustomize/kyaml/kio"
        "sigs.k8s.io/kustomize/kyaml/yaml"
)

type SecretGenerator struct {
        Metadata struct {
                Name      string `yaml:"name"`
                Namespace string `yaml:"namespace"`
        } `yaml:"metadata"`
        Spec struct {
                SecretName     string            `yaml:"secretName"`
                SecretMappings map[string]string `yaml:"secretMappings"`
        } `yaml:"spec"`
}

func (p *SecretGenerator) Generate() (*yaml.RNode, error) {
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
                secretData[secretKey] = base64Encode(secretValue)
        }

        return yaml.FromMap(map[string]interface{}{
                "apiVersion": "v1",
                "kind":       "Secret",
                "metadata": map[string]string{
                        "name":      p.Spec.SecretName,
                        "namespace": p.Metadata.Namespace,
                        "annotations": map[string]string{
                                "secret-source": "google-secret-manager",
                        },
                },
                "type": "Opaque",
                "data": secretData,
        })
}

func fetchSecretFromGSM(ctx context.Context, client *secretmanager.Client, gsmSecretName string) (string, error) {
        accessRequest := &secretmanagerpb.AccessSecretVersionRequest{
                Name: gsmSecretName + "/versions/latest",
        }

        result, err := client.AccessSecretVersion(ctx, accessRequest)
        if err != nil {
                return "", fmt.Errorf("failed to access secret version: %v", err)
        }

        return string(result.Payload.Data), nil
}

func base64Encode(input string) string {
	return base64.StdEncoding.EncodeToString([]byte(input))
}

func main() {
        var p SecretGenerator
        cmd := framework.Command(&p, func(items []*yaml.RNode) ([]*yaml.RNode, error) {
                for i := range items {
                        if items[i].GetApiVersion() == "my.kustomize.plugins/v1" && items[i].GetKind() == "SecretGenerator" {
                                if err := yaml.Unmarshal([]byte(items[i].MustString()), &p); err != nil {
                                        return nil, err
                                }

                                generatedSecret, err := p.Generate()
                                if err != nil {
                                        return nil, err
                                }

                                // Append the generated secret to the resource list
                                items = append(items, generatedSecret)
                        }
                }
                return items, nil
        })

        if err := cmd.Execute(); err != nil {
                fmt.Fprintf(os.Stderr, "error: %v\n", err)
                os.Exit(1)
        }
}
