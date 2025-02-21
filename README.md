# Built-in Auth for Azure Container Apps with Entra ID

This repository includes all the Bicep (infrastructure-as-code) necessary to provision an Azure Container App with the [built-in authentication feature](https://learn.microsoft.com/azure/container-apps/authentication) and a Microsoft Entra ID identity provider. The Bicep files use the new [Microsoft Graph extension (public preview)](https://learn.microsoft.com/graph/templates/overview-bicep-templates-for-graph) to create the Entra application registration using [managed identity with Federated Identity Credentials](https://learn.microsoft.com/azure/container-apps/managed-identity), so that no client secrets or certificates are necessary.

* [Getting started](#getting-started)
  * [GitHub Codespaces](#github-codespaces)
  * [VS Code Dev Containers](#vs-code-dev-containers)
  * [Local environment](#local-environment)
* [Deploying](#deploying)
* [Costs](#costs)
* [Local development](#local-development)

## Getting started

You have a few options for getting started with this template.
The quickest way to get started is GitHub Codespaces, since it will setup all the tools for you, but you can also [set it up locally](#local-environment).

### GitHub Codespaces

You can run this template virtually by using GitHub Codespaces. The button will open a web-based VS Code instance in your browser:

1. Open the template (this may take several minutes):

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/containerapps-builtinauth-bicep)

2. Open a terminal window
3. Continue with the [deploying steps](#deploying)

### VS Code Dev Containers

A related option is VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/containerapps-builtinauth-bicep)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the [deploying steps](#deploying)

### Local environment

If you're not using one of the above options for opening the project, then you'll need to:

1. Make sure the following tools are installed:

    * [Azure Developer CLI (azd) 1.12+](https://aka.ms/install-azd)
    * [Python 3.9+](https://www.python.org/downloads/): Only needed for local development.
    * [Git](https://git-scm.com/downloads)

2. Download the project code:

    ```shell
    azd init -t containerapps-builtinauth-bicep
    ```

3. Open the project folder in your terminal or editor.

4. Continue with the [deploying steps](#deploying).

## Deploying

Once you've opened the project in [Codespaces](#github-codespaces), in [Dev Containers](#vs-code-dev-containers), or [locally](#local-environment), you can deploy it to Azure.

Steps for deployment:

1. Sign up for a [free Azure account](https://azure.microsoft.com/free/) and create an Azure subscription.
2. Login to Azure:

    ```shell
    azd auth login
    ```

3. Provision and deploy all the resources:

    ```shell
    azd up
    ```

    It will prompt you to login and to provide a name (like "authapp") and location (like "eastus"). Then it will provision the resources in your account and deploy the latest code.

4. When `azd` has finished deploying, you'll see an endpoint URI in the command output. Visit that URI, and you should get prompted to login. Once you login, you should see a basic webpage. If you see an error, open the Azure Portal from the URL in the command output, navigate to the Container App, select Logstream, and check the logs for any errors.

5. Remember to take down your app if it's no longer in use, either by deleting the resource group in the Portal or running `azd down`.

## Costs

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage. You can try the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) for the resources:

* Azure Container App: Consumption tier with 0.5 CPU, 1GiB memory/storage. Pricing is based on resource allocation, and each month allows for a certain amount of free usage. [Pricing](https://azure.microsoft.com/pricing/details/container-apps/)
* Azure Container Registry: Basic tier. [Pricing](https://azure.microsoft.com/pricing/details/container-registry/)
* Microsoft Entra: Free for up to 50,000 monthly active users. [Pricing](https://www.microsoft.com/security/business/microsoft-entra-pricing)

⚠️ To reduce unnecessary costs, remember to take down your app if it's no longer in use,
either by deleting the resource group in the Portal or running `azd down`.

## Local development

The built-in auth feature is only available when the app is deployed to Azure Container Apps. However, you can run the app locally to test the app's functionality.

1. Create a [Python virtual environment](https://docs.python.org/3/tutorial/venv.html#creating-virtual-environments) and activate it.

2. Install requirements:

    ```shell
    python3 -m pip install -r requirements.txt
    ```

3. Run the server:

    ```shell
    python3 -m flask run --port 50505 --debug
    ```

4. Click 'http://127.0.0.1:50505' in the terminal, which should open the website in a new tab.
5. Try the index page, try '/hello?name=yourname', and try other paths.
