import AsyncStorage from '@react-native-async-storage/async-storage';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { refreshGarments, uploadGarmentPhoto } from '@/lib/garments';

const MAX_PHOTO_WIDTH = 1600;
const MAX_ATTEMPTS = 3;
const CONCURRENT_UPLOADS = 2;

type QueuedPhoto = {
  id: string;
  uri: string;
  status: 'pending' | 'uploading' | 'failed';
  attempts: number;
};

type UploadQueueState = {
  photos: QueuedPhoto[];
};

// Saved on the phone so closing the app in the middle of a batch loses nothing.
export const useUploadQueue = create<UploadQueueState>()(
  persist(() => ({ photos: [] as QueuedPhoto[] }), {
    name: 'upload-queue',
    storage: createJSONStorage(() => AsyncStorage),
    onRehydrateStorage: () => () => resumeUploads(),
  })
);

function patchPhoto(id: string, patch: Partial<QueuedPhoto>): void {
  useUploadQueue.setState(({ photos }) => ({
    photos: photos.map((photo) => (photo.id === id ? { ...photo, ...patch } : photo)),
  }));
}

function removePhoto(id: string): void {
  useUploadQueue.setState(({ photos }) => ({ photos: photos.filter((photo) => photo.id !== id) }));
}

async function compress(uri: string): Promise<string> {
  const image = await ImageManipulator.manipulate(uri)
    .resize({ width: MAX_PHOTO_WIDTH })
    .renderAsync();
  const saved = await image.saveAsync({ compress: 0.8, format: SaveFormat.JPEG });
  return saved.uri;
}

async function uploadOne(photo: QueuedPhoto): Promise<void> {
  patchPhoto(photo.id, { status: 'uploading' });
  try {
    await uploadGarmentPhoto(photo.uri);
    removePhoto(photo.id);
    void refreshGarments();
  } catch {
    const attempts = photo.attempts + 1;
    patchPhoto(photo.id, { attempts, status: attempts < MAX_ATTEMPTS ? 'pending' : 'failed' });
  }
  pump();
}

function pump(): void {
  const { photos } = useUploadQueue.getState();
  const freeSlots = CONCURRENT_UPLOADS - photos.filter((p) => p.status === 'uploading').length;
  photos
    .filter((photo) => photo.status === 'pending')
    .slice(0, Math.max(freeSlots, 0))
    .forEach((photo) => void uploadOne(photo));
}

function resumeUploads(): void {
  // Anything marked as uploading was interrupted when the app closed.
  useUploadQueue.setState(({ photos }) => ({
    photos: photos.map((photo) =>
      photo.status === 'uploading' ? { ...photo, status: 'pending' } : photo
    ),
  }));
  pump();
}

export async function enqueuePhoto(uri: string): Promise<void> {
  const compressedUri = await compress(uri);
  const photo: QueuedPhoto = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    uri: compressedUri,
    status: 'pending',
    attempts: 0,
  };
  useUploadQueue.setState(({ photos }) => ({ photos: [...photos, photo] }));
  pump();
}

export function retryFailedUploads(): void {
  useUploadQueue.setState(({ photos }) => ({
    photos: photos.map((photo) =>
      photo.status === 'failed' ? { ...photo, status: 'pending', attempts: 0 } : photo
    ),
  }));
  pump();
}

export function discardFailedUploads(): void {
  useUploadQueue.setState(({ photos }) => ({
    photos: photos.filter((photo) => photo.status !== 'failed'),
  }));
}
