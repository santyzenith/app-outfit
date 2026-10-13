// Set EXPO_PUBLIC_API_URL in mobile/.env to the computer's LAN address when testing on a phone.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';
