import Constants from 'expo-constants';

// In development the backend runs on the same computer as Metro, so its address follows the LAN IP.
function devApiUrl(): string | undefined {
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return host ? `http://${host}:8000` : undefined;
}

// EXPO_PUBLIC_API_URL wins when set, e.g. for a build that talks to the real server.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? devApiUrl() ?? 'http://localhost:8000';
