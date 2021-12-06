# RHC4TP OpenShift Cluster Setup

The release pipeline publishes bundle images to registry.connect.redhat.com. The registry
behind that address is the RHC4TP OpenShift cluster. The following steps must be performed
to prepare the RHC4TP clusters for use by the pipeline. 

1. Login to the chosen cluster

1. Create a service account

    ```bash
    oc create sa operator-pipelines -n default
    ```

1. Create a kubeconfig for the service account. It should be stored in the repository Ansible Vault.

    ```bash
    clusterName=dev
    namespace=default
    serviceAccount=operator-pipelines
    server=$(oc cluster-info | grep "is running at" | sed "s/Kubernetes master//" | sed "s/ is running at //")
    # Sometimes the token secret is first in the serviceAccount, sometimes it's second after Dockerconfig
    secretName=$(oc --namespace $namespace get serviceAccount $serviceAccount -o jsonpath='{.secrets[1].name}')
    ca=$(oc --namespace $namespace get secret/$secretName -o jsonpath='{.data.ca\.crt}')
    token=$(oc --namespace $namespace get secret/$secretName -o jsonpath='{.data.token}' | base64 --decode)

    echo "
    ---
    apiVersion: v1
    kind: Config
    clusters:
      - name: ${clusterName}
        cluster:
          certificate-authority-data: ${ca}
          server: ${server}
    contexts:
      - name: ${serviceAccount}@${clusterName}
        context:
          cluster: ${clusterName}
          namespace: ${serviceAccount}
          user: ${serviceAccount}
    users:
      - name: ${serviceAccount}
        user:
          token: ${token}
    current-context: ${serviceAccount}@${clusterName}
    "
    ```

1. Grant the service account the permissions to create projects and manage existing ones.
Permissions are this high as we have to update roles in projects created by other service accounts.

    ```bash
    oc adm policy add-cluster-role-to-user cluster-admin -z operator-pipelines -n default
    ```

1. Create the dockerconfig secret, containing the credentials to registry that stores the images to be published

    ```bash
    cat << EOF > registry-secret.yml
    apiVersion: v1
    kind: Secret
    metadata:
      name: registry-dockerconfig-secret
    data:
      .dockerconfigjson: < BASE64 ENCODED DOCKER CONFIG >
    type: kubernetes.io/dockerconfigjson
    EOF

    oc create -f registry-secret.yml
    ```

1. Link this secret with the created service account 

    ```bash
    oc secret link operator-pipelines registry-dockerconfig-secret
    ```
