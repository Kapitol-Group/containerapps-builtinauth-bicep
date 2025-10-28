import React from 'react';
import { PublicClientApplication } from '@azure/msal-browser';
import { v4 as uuidv4 } from 'uuid';
import { msalInstance, getDelegatedToken, useLogin } from '../authConfig';

interface SharePointFilePickerProps {
  baseUrl: string;
  tenderSitePath?: string;
  tenderFolder?: string;
  filters?: string[];
  onFilePicked?: (data: any) => void;
  buttonText?: string;
  className?: string;
}

export const SharePointFilePicker: React.FC<SharePointFilePickerProps> = ({
  baseUrl,
  tenderSitePath = '/sites/KapitolGroupNewBusinessTeam/Shared Documents',
  tenderFolder = '/01 TENDERS/Active/',
  filters = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt'],
  onFilePicked,
  buttonText = 'Browse SharePoint',
  className = '',
}) => {
  let win: Window | null = null;
  let port: MessagePort | null = null;

  function combine(...paths: string[]): string {
    return paths
      .map((path) => path.replace(/^[\\|/]/, '').replace(/[\\|/]$/, ''))
      .join('/')
      .replace(/\\/g, '/');
  }

  const handleClick = async () => {
    try {
      const channelId = uuidv4();
      const pickerOptions: any = {
        sdk: '8.0',
        entry: {
          sharePoint: tenderSitePath
            ? {
                byPath: {
                  list: tenderSitePath,
                  folder: tenderSitePath + tenderFolder,
                  fallbackToRoot: true,
                },
              }
            : {
                // Default to OneDrive if no SharePoint path provided
                oneDrive: {},
              },
        },
        messaging: {
          origin: window.location.origin,
          channelId: channelId,
        },
        typesAndSources: {
          mode: 'all',
          filters: filters,
          pivots: {
            oneDrive: true,
            recent: true,
          },
        },
      };

      // Add SharePoint pivot if path is provided
      if (tenderSitePath) {
        pickerOptions.typesAndSources.pivots.site = true;
        pickerOptions.typesAndSources.pivots.shared = true;
      }

      const token = useLogin ? await getDelegatedToken(msalInstance, baseUrl) : undefined;
      if (!token && useLogin) {
        console.error('Failed to get delegated token for SharePoint');
        alert('Failed to authenticate with SharePoint. Please try again.');
        return;
      }

      // Initialize the OneDrive/SharePoint picker
      const queryString = new URLSearchParams({
        filePicker: JSON.stringify(pickerOptions),
      });
      const url = combine(baseUrl, `_layouts/15/FilePicker.aspx?${queryString}`);
      win = window.open('', 'Picker', 'width=1024,height=600');
      if (!win) {
        console.error('Failed to open picker window');
        alert('Failed to open file picker. Please allow popups for this site.');
        return;
      }

      const form = win.document.createElement('form');
      form.setAttribute('action', url);
      form.setAttribute('method', 'POST');
      win.document.body.append(form);

      if (token) {
        const input = win.document.createElement('input');
        input.setAttribute('type', 'hidden');
        input.setAttribute('name', 'access_token');
        input.setAttribute('value', token);
        form.appendChild(input);
      }

      form.submit();

      window.addEventListener('message', (event) => {
        if (event.source && event.source === win) {
          const message = event.data;

          if (
            message.type === 'initialize' &&
            message.channelId === pickerOptions.messaging.channelId
          ) {
            port = event.ports[0];
            port.addEventListener('message', messageListener);
            port.start();
            port.postMessage({
              type: 'activate',
            });
          }
        }
      });
    } catch (error) {
      console.error('Error opening SharePoint picker:', error);
      alert('An error occurred while opening the file picker.');
    }
  };

  const messageListener = async (message: MessageEvent) => {
    switch (message.data.type) {
      case 'notification':
        break;

      case 'command':
        if (!port) {
          console.error('No port available for command message');
          return;
        }
        port.postMessage({
          type: 'acknowledge',
          id: message.data.id,
        });

        const command = message.data.data;

        switch (command.command) {
          case 'authenticate':
            const token = useLogin
              ? await getDelegatedToken(msalInstance, command.resource)
              : undefined;

            if (typeof token !== 'undefined' && token !== null) {
              port.postMessage({
                type: 'result',
                id: message.data.id,
                data: {
                  result: 'token',
                  token,
                },
              });
            } else {
              console.error(`Could not get auth token for command: ${JSON.stringify(command)}`);
            }
            break;

          case 'close':
            if (!win) {
              console.error('No window to close');
              return;
            }
            win.close();
            break;

          case 'pick':
            // Call the parent callback with the picked data
            if (onFilePicked && typeof onFilePicked === 'function') {
              onFilePicked(command);
            }

            port.postMessage({
              type: 'result',
              id: message.data.id,
              data: {
                result: 'success',
              },
            });

            if (!win) {
              console.error('No window to close');
              return;
            }
            win.close();
            break;

          default:
            port.postMessage({
              result: 'error',
              error: {
                code: 'unsupportedCommand',
                message: command.command,
              },
              isExpected: true,
            });
            break;
        }
        break;
    }
  };

  return (
    <button type="button" className={`btn-secondary ${className}`} onClick={handleClick}>
      📁 {buttonText}
    </button>
  );
};
