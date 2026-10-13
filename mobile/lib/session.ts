import * as SecureStore from 'expo-secure-store';
import { AppState } from 'react-native';
import { create } from 'zustand';

import { API_URL } from '@/lib/config';

const REFRESH_TOKEN_KEY = 'refresh_token';
// Renew a little before the access token actually expires.
const EXPIRY_MARGIN_MS = 60_000;

export type User = {
  id: string;
  email: string | null;
  display_name: string | null;
  is_guest: boolean;
};

type SessionResponse = {
  user: User;
  access_token: string;
  refresh_token: string;
  expires_in: number;
};

type SessionState = {
  status: 'loading' | 'ready' | 'error';
  user: User | null;
  accessToken: string | null;
  expiresAt: number;
};

export const useSession = create<SessionState>(() => ({
  status: 'loading',
  user: null,
  accessToken: null,
  expiresAt: 0,
}));

let refreshTimer: ReturnType<typeof setTimeout> | undefined;
let pendingRefresh: Promise<void> | null = null;

class RejectedError extends Error {}

async function postAuth(path: string, body?: object): Promise<SessionResponse> {
  const response = await fetch(`${API_URL}/v1/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 401) throw new RejectedError();
  if (!response.ok) throw new Error(`auth/${path} failed with ${response.status}`);
  return response.json();
}

async function applySession(session: SessionResponse): Promise<void> {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, session.refresh_token);
  const lifetimeMs = session.expires_in * 1000;
  useSession.setState({
    status: 'ready',
    user: session.user,
    accessToken: session.access_token,
    expiresAt: Date.now() + lifetimeMs,
  });
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => void refreshSession(), lifetimeMs - EXPIRY_MARGIN_MS);
}

async function openSession(): Promise<void> {
  const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  if (refreshToken) {
    try {
      return await applySession(await postAuth('refresh', { refresh_token: refreshToken }));
    } catch (error) {
      // Only a rejected token means the session is gone; a network error must not discard it.
      if (!(error instanceof RejectedError)) throw error;
    }
  }
  await applySession(await postAuth('guest'));
}

export function refreshSession(): Promise<void> {
  // Concurrent callers share one request: a refresh token can only be used once.
  pendingRefresh ??= openSession().finally(() => {
    pendingRefresh = null;
  });
  return pendingRefresh;
}

export async function startSession(): Promise<void> {
  useSession.setState({ status: 'loading' });
  try {
    await refreshSession();
  } catch {
    useSession.setState({ status: 'error' });
  }
}

export async function getAccessToken(): Promise<string> {
  const { accessToken, expiresAt } = useSession.getState();
  if (accessToken && expiresAt - Date.now() > EXPIRY_MARGIN_MS) return accessToken;
  await refreshSession();
  return useSession.getState().accessToken ?? '';
}

// Timers do not run while the app is in the background, so check again on return.
AppState.addEventListener('change', (state) => {
  if (state === 'active' && useSession.getState().status === 'ready') {
    void getAccessToken().catch(() => undefined);
  }
});
