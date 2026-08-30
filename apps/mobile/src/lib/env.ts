const DEFAULT_API_URL = 'http://localhost:5000';

function requireValidUrl(value: string | undefined, fallback: string): string {
  const candidate = value?.trim() || fallback;
  try {
    return new URL(candidate).toString().replace(/\/$/, '');
  } catch {
    throw new Error('EXPO_PUBLIC_API_URL must be a valid absolute URL.');
  }
}

export const env = Object.freeze({
  apiUrl: requireValidUrl(process.env.EXPO_PUBLIC_API_URL, DEFAULT_API_URL),
});
