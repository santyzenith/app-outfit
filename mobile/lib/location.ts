import * as Location from 'expo-location';
import * as React from 'react';

export type Coords = { lat: number; lon: number };

const LOCATION_TIMEOUT_MS = 5000;

async function readCoords(): Promise<Coords | null> {
  const { granted } = await Location.requestForegroundPermissionsAsync();
  if (!granted) return null;

  // City-level precision is enough for weather, so a recent known position is fine.
  const position =
    (await Location.getLastKnownPositionAsync()) ??
    (await Promise.race([
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low }),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), LOCATION_TIMEOUT_MS)),
    ]));
  return position ? { lat: position.coords.latitude, lon: position.coords.longitude } : null;
}

// undefined while still asking, null when the location is not available.
export function useCoords(): Coords | null | undefined {
  const [coords, setCoords] = React.useState<Coords | null | undefined>(undefined);

  React.useEffect(() => {
    readCoords()
      .catch(() => null)
      .then(setCoords);
  }, []);

  return coords;
}
