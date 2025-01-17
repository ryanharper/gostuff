package main

import (
        "fmt"
        "os"
        "os/exec"

        "sigs.k8s.io/kustomize/api/resmap"
        "sigs.k8s.io/kustomize/api/resource"
        "sigs.k8s.io/kustomize/api/types"
        "sigs.k8s.io/kustomize/kyaml/kio"
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
                        &KustomizePlugin, // Now correctly using the Filter interface
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

// Filter implements the kio.Filter interface
func (p *plugin) Filter(input []*yaml.RNode) ([]*yaml.RNode, error) {
    // Call the Generate function to create the secret resource
    rm, err := p.Generate()
    if err != nil {
        return nil, err
    }

    // Convert the ResMap to []*yaml.RNode
    var output []*yaml.RNode
    for _, r := range rm.Resources() {
        output = append(output, r.RNode)
    }

    // Return the generated resources
    return output, nil
}

func (p *plugin) Generate() (resmap.ResMap, error) {
        // Fetch the secret value from GSM
        secretValue, err := fetchSecretFromGSM(p.Spec.GsmSecretName, p.Spec.GsmSecretVersion)
        if err != nil {
                return nil, err
