package main

import (
        "fmt"
        "os"
        "os/exec"

        "sigs.k8s.io/kustomize/api/resmap"
        "sigs.k8s.io/kustomize/api/resource"
        "sigs.k8s.io/kustomize/api/types"
        "sigs.k8s.io/kustomize/kyaml/kio"
        "sigs.k8s.io/kustomize/kyaml/kio/kioutil"
        "sigs.k8s.io/kustomize/kyaml/yaml"
)

type plugin struct {
        resmap.ResMap
        types.ObjectMeta `json:"metadata,omitempty" yaml:"metadata,omitempty" protobuf:"bytes,1,opt,name=metadata"`
        Spec           struct {
                SecretName        string `json:"secretName,omitempty" yaml:"secretName,omitempty"`
                GsmSecretName     string `json:"gsmSecretName,omitempty" yaml:"gsmSecretName,omitempty"`
                GsmSecretVersion  string `json:"gsmSecretVersion,omitempty" yaml:"gsmSecretVersion,omitempty"`
                SecretKey         string `json:"secretKey,omitempty" yaml:"secretKey,omitempty"`
        } `json:"spec,omitempty" yaml:"spec,omitempty"`

}

//nolint: go-lint
var KustomizePlugin plugin

func main() {
        rw := &kio.ByteReadWriter{
                Reader:                os.Stdin,
                Writer:                os.Stdout,
                KeepReaderAnnotations: true,
        }

        err := kio.Pipeline{
                Inputs: []kio.Reader{rw},
                Filters: []kio.Filter{
                        &KustomizePlugin,
                },
                Outputs: []kio.Writer{rw},
        }.Execute()

        if err != nil {
                fmt.Fprintf(os.Stderr, "Error executing pipeline: %v\n", err)
                os.Exit(1)
        }
}

func (p *plugin) Config(
        _ *resmap.PluginHelpers, c []byte) (err error) {
        return yaml.Unmarshal(c, p)
}

func (p *plugin) Generate() (resmap.ResMap, error) {
        // Fetch the secret value from GSM
        secretValue, err := fetchSecretFromGSM(p.Spec.GsmSecretName, p.Spec.GsmSecretVersion)
        if err != nil {
                return nil, err
        }

        // Create a Kubernetes Secret
        secret := &resource.Resource{
                RNode: *yaml.NewRNode(&yaml.Node{
                        Kind: yaml.MappingNode,
                        Tag:  "!!map",
                }),
        }
        secret.SetApiVersion("v1")
        secret.SetKind("Secret")
        secret.SetName(p.Spec.SecretName)
        secret.SetNamespace(p.ObjectMeta.Namespace) // Set the namespace if available

        // Add the secret data
        err = secret.PipeE(
                yaml.SetField("type", yaml.NewStringRNode("Opaque")),
                yaml.SetField("data", yaml.NewMapRNode(&map[string]string{
                        p.Spec.SecretKey: secretValue,
                })),
        )
        if err != nil {
                return nil, err
        }

        // Add an annotation to indicate that this secret was generated from GSM
        if err := secret.SetAnnotation("secret-source", "google-secret-manager"); err != nil {
                return nil, err
        }
        rm := resmap.New()

        err = rm.Append(secret)
        return rm, err
}

func fetchSecretFromGSM(secretName, secretVersion string) (string, error) {
        // Execute the fetch-secret.sh script
        cmd := exec.Command("./fetch-secret.sh", secretName, secretVersion)
        output, err := cmd.Output()
        if err != nil {
                return "", fmt.Errorf("failed to fetch secret from GSM: %v", err)
        }

        return string(output), nil
}
