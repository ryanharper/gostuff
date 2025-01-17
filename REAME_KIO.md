# SKaffold README
Create a Kustomize Exec KRM Plugin Configuration

This file tells Kustomize how to use our fetch-secret.sh script as a plugin. It will define the plugin kind and structure how the secret data will be formed.

Create a file named SecretGenerator.yaml:

``YAML

apiVersion: my.kustomize.plugins/v1
kind: SecretGenerator
metadata:
  name: secret-generator-config
spec:
  secretName: my-gsm-secret # The name of the Kubernetes Secret to be created
  gsmSecretName: projects/YOUR_PROJECT_ID/secrets/YOUR_SECRET_NAME # The full resource name of your secret in GSM
  gsmSecretVersion: latest  # The version of the secret (e.g., latest, 1, 2, etc.)
  secretKey: mysecretkey # The key inside the Kubernetes Secret where the value

```


Here's an example script (e.g., fetch-secret.sh):

```Bash

#!/bin/bash

# Get the secret name and version from environment variables
SECRET_NAME=$1
SECRET_VERSION=$2

# Check if both parameters are provided
if [ -z "$SECRET_NAME" ] || [ -z "$SECRET_VERSION" ]; then
  echo "Error: Both SECRET_NAME and SECRET_VERSION must be provided." >&2
  exit 1
fi

# Fetch the secret using gcloud
gcloud secrets versions access "$SECRET_VERSION" --secret="$SECRET_NAME"
```

Integrate into Your kustomization.yaml

Now, you need to configure Kustomize to use this plugin in your main kustomization.yaml file.

```YAML

apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

generators:
- ./SecretGenerator.yaml # Path to your plugin configuration file

configurations:
  - kustomize-plugin-config.yaml

resources:
- deployment.yaml # Your other Kubernetes resources...
Create a kustomize-plugin-config.yaml file:
```


```YAML

# Enable KRM plugins
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: KustomizationPluginConfig
metadata:
  name: enable-krm-plugins
configurations:
- name: my.kustomize.plugins/v1
  types:
  - SecretGenerator
````

```YAML
apiVersion: my.kustomize.plugins/v1
kind: SecretGenerator
metadata:
  name: secret-generator-config
spec:
  secretName: my-gsm-secret # The name of the Kubernetes Secret to be created
  gsmSecretName: projects/YOUR_PROJECT_ID/secrets/YOUR_SECRET_NAME # The full resource name of your secret in GSM
  gsmSecretVersion: latest  # The version of the secret (e.g., latest, 1, 2, etc.)
  secretKey: mysecretkey # The key inside the Kubernetes Secret where the value will be stored
```
