import { Configuration, PublicClientApplication } from '@azure/msal-browser';

// Get build-time environment variables for SharePoint picker
const entraClientId = import.meta.env.VITE_ENTRA_CLIENT_ID || '';
const entraTenantId = import.meta.env.VITE_ENTRA_TENANT_ID || '';

// MSAL configuration using build-time env vars (for SharePoint picker)
export const msalConfig: Configuration = {
    auth: {
        clientId: entraClientId,
        authority: entraTenantId
            ? `https://login.microsoftonline.com/${entraTenantId}`
            : undefined,
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

// Track if configuration has been loaded from backend (for Graph API)
let backendConfigLoaded = false;
let backendConfigPromise: Promise<void> | null = null;
let graphApiClientId = '';
let graphApiTenantId = '';

// Load configuration from backend for Graph API token requests
async function loadConfigFromBackend(): Promise<void> {
    if (backendConfigLoaded) {
        return;
    }

    try {
        const response = await fetch('/api/config');
        const result = await response.json();

        if (result.success && result.data) {
            const { entraClientId, entraTenantId } = result.data;

            if (entraClientId && entraTenantId) {
                graphApiClientId = entraClientId;
                graphApiTenantId = entraTenantId;

                console.log('Backend configuration loaded for Graph API');
                console.log('Graph API Client ID:', entraClientId);
                console.log('Graph API Tenant ID:', entraTenantId);

                backendConfigLoaded = true;
            } else {
                console.warn('Entra credentials not configured on backend');
            }
        } else {
            console.error('Failed to load config from backend:', result.error);
        }
    } catch (error) {
        console.error('Error loading config from backend:', error);
    }
}

// Initialize MSAL with build-time configuration (for SharePoint picker)
export const initializeMsal = async () => {
    // Only initialize if we have a client ID
    if (!msalConfig.auth.clientId) {
        console.log('No Entra Client ID configured, skipping MSAL initialization');
        return;
    }

    await msalInstance.initialize();

    // Handle redirect promise
    await msalInstance.handleRedirectPromise();

    // Set active account if one exists
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length > 0) {
        msalInstance.setActiveAccount(accounts[0]);
    }
};

// Get delegated token for SharePoint (uses build-time config)
export const getDelegatedToken = async (
    client: PublicClientApplication,
    resource: string
): Promise<string | undefined> => {
    // Ensure MSAL is initialized
    try {
        await client.initialize();
    } catch (error) {
        // Already initialized, ignore error
        console.log('MSAL already initialized or initialization error:', error);
    }

    const newTokenRequest = {
        ...tokenRequest,
        scopes: [resource + '/.default'],
    };

    console.log('Requesting delegated token with scopes:', newTokenRequest.scopes);

    let activeAccount = client.getActiveAccount();

    // If no active account, try to get one from all accounts
    if (!activeAccount) {
        console.log('No active account found, checking all accounts...');
        const accounts = client.getAllAccounts();
        if (accounts.length > 0) {
            activeAccount = accounts[0];
            client.setActiveAccount(activeAccount);
            console.log('Set active account from existing accounts:', activeAccount.username);
        } else {
            console.log('No accounts found, attempting interactive login...');
            // No accounts at all, need to login
            try {
                const loginResponse = await client.loginPopup({
                    ...newTokenRequest,
                    prompt: 'select_account',
                });
                if (loginResponse.account) {
                    client.setActiveAccount(loginResponse.account);
                    activeAccount = loginResponse.account;
                    console.log('Active account set after login popup:', activeAccount.username);
                } else {
                    console.error('No account returned from login popup');
                    return undefined;
                }
            } catch (loginError) {
                console.error('Login popup failed:', loginError);
                return undefined;
            }
        }
    }

    if (!activeAccount) {
        console.error('Still no active account after attempting to get one');
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
            try {
                const resp = await client.acquireTokenPopup(newTokenRequest);
                console.log('Token acquired via popup');
                return resp.accessToken;
            } catch (popupError) {
                console.error('Token acquisition via popup failed:', popupError);
                return undefined;
            }
        });
};

// Get delegated token for Graph API (uses runtime backend config)
export const getGraphApiToken = async (
    resource: string
): Promise<string | undefined> => {
    // Load backend config if not already loaded
    if (!backendConfigPromise) {
        backendConfigPromise = loadConfigFromBackend();
    }
    await backendConfigPromise;

    // Check if we have backend config
    if (!graphApiClientId || !graphApiTenantId) {
        console.error('Backend configuration not loaded for Graph API');
        return undefined;
    }

    // Create a separate MSAL instance for Graph API with backend config
    const graphApiMsalConfig: Configuration = {
        auth: {
            clientId: graphApiClientId,
            authority: `https://login.microsoftonline.com/${graphApiTenantId}`,
            redirectUri: window.location.origin,
        },
        cache: {
            cacheLocation: 'sessionStorage',
            storeAuthStateInCookie: false,
        },
    };

    const graphApiClient = new PublicClientApplication(graphApiMsalConfig);
    await graphApiClient.initialize();

    const newTokenRequest = {
        ...tokenRequest,
        scopes: [resource + '/.default'],
    };

    console.log('Requesting Graph API token with scopes:', newTokenRequest.scopes);

    let activeAccount = graphApiClient.getActiveAccount();

    // If no active account, try to get one from all accounts
    if (!activeAccount) {
        console.log('No active account found for Graph API, checking all accounts...');
        const accounts = graphApiClient.getAllAccounts();
        if (accounts.length > 0) {
            activeAccount = accounts[0];
            graphApiClient.setActiveAccount(activeAccount);
            console.log('Set active account from existing accounts:', activeAccount.username);
        } else {
            console.log('No accounts found for Graph API, attempting interactive login...');
            // No accounts at all, need to login
            try {
                const loginResponse = await graphApiClient.loginPopup({
                    ...newTokenRequest,
                    prompt: 'select_account',
                });
                if (loginResponse.account) {
                    graphApiClient.setActiveAccount(loginResponse.account);
                    activeAccount = loginResponse.account;
                    console.log('Active account set after login popup:', activeAccount.username);
                } else {
                    console.error('No account returned from login popup');
                    return undefined;
                }
            } catch (loginError) {
                console.error('Login popup failed:', loginError);
                return undefined;
            }
        }
    }

    if (!activeAccount) {
        console.error('Still no active account after attempting to get one');
        return undefined;
    }

    console.log('Active account for Graph API token request:', activeAccount.username);

    return graphApiClient
        .acquireTokenSilent({
            ...newTokenRequest,
            redirectUri: window.location.origin,
            account: activeAccount,
        })
        .then((r) => r.accessToken)
        .catch(async (error) => {
            console.log('Error acquiring Graph API token silently:', error);
            // If silent token acquisition fails, try to acquire token interactively
            try {
                const resp = await graphApiClient.acquireTokenPopup(newTokenRequest);
                console.log('Graph API token acquired via popup');
                return resp.accessToken;
            } catch (popupError) {
                console.error('Graph API token acquisition via popup failed:', popupError);
                return undefined;
            }
        });
};

// Check if we're using MSAL (client ID is configured at build time)
export const useLogin = !!entraClientId;
