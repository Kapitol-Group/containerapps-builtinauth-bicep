import { Configuration, PublicClientApplication } from '@azure/msal-browser';

// MSAL configuration
export const msalConfig: Configuration = {
    auth: {
        clientId: import.meta.env.VITE_ENTRA_CLIENT_ID || '',
        authority: `https://login.microsoftonline.com/${import.meta.env.VITE_ENTRA_TENANT_ID || 'common'}`,
        redirectUri: window.location.origin,
    },
    cache: {
        cacheLocation: 'sessionStorage',
        storeAuthStateInCookie: false,
    },
};

// Add scopes for SharePoint access
export const tokenRequest = {
    scopes: ['User.Read', 'Files.Read.All', 'Sites.Read.All'],
};

// Create the MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig);

// Initialize MSAL
export const initializeMsal = async () => {
    await msalInstance.initialize();

    // Handle redirect promise
    await msalInstance.handleRedirectPromise();

    // Set active account if one exists
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length > 0) {
        msalInstance.setActiveAccount(accounts[0]);
    }
};

// Get delegated token for SharePoint
export const getDelegatedToken = async (
    client: PublicClientApplication,
    resource: string
): Promise<string | undefined> => {
    const newTokenRequest = {
        ...tokenRequest,
        scopes: [resource + '/.default'],
    };

    console.log('Requesting delegated token with scopes:', newTokenRequest.scopes);

    const activeAccount = client.getActiveAccount();
    if (!activeAccount) {
        console.error('No active account found for delegated token request');
        return undefined;
    }

    console.log('Active account for delegated token request:', activeAccount.username);

    return client
        .acquireTokenSilent({
            ...newTokenRequest,
            redirectUri: window.location.origin,
            account: activeAccount,
        })
        .then((r) => r.accessToken)
        .catch(async (error) => {
            console.log('Error acquiring token silently:', error);
            // If silent token acquisition fails, try to acquire token interactively
            const resp = await client.loginPopup(newTokenRequest);
            if (!resp.account) {
                console.error('No account found after login popup');
                return undefined;
            }
            client.setActiveAccount(resp.account);
            console.log('Active account set after login popup:', resp.account.username);
            // If the login was successful, try to acquire the token again

            if (resp.idToken) {
                console.log('ID token received after login popup:', resp.idToken);
                const resp2 = await client.acquireTokenSilent(newTokenRequest);
                return resp2.accessToken;
            }
            console.error('No ID token received after login popup');
            return undefined;
        });
};

// Check if we're using MSAL (client ID is configured)
export const useLogin = !!import.meta.env.VITE_ENTRA_CLIENT_ID;
