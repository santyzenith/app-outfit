import { View } from 'react-native';

import { Spinner } from '@/components/app/spinner';
import { Button } from '@/components/ui/button';
import { Text } from '@/components/ui/text';
import { discardFailedUploads, retryFailedUploads, useUploadQueue } from '@/lib/upload-queue';

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function UploadBanner() {
  const photos = useUploadQueue((state) => state.photos);
  const failed = photos.filter((photo) => photo.status === 'failed').length;
  const inProgress = photos.length - failed;

  if (photos.length === 0) return null;

  return (
    <View className="gap-2 border-b border-border bg-card px-4 py-3">
      {inProgress > 0 && (
        <View className="flex-row items-center gap-3">
          <Spinner size="small" />
          <Text className="text-sm">Subiendo {plural(inProgress, 'foto', 'fotos')}…</Text>
        </View>
      )}
      {failed > 0 && (
        <View className="flex-row items-center justify-between gap-2">
          <Text className="flex-1 text-sm">
            {plural(failed, 'foto no se pudo subir', 'fotos no se pudieron subir')}
          </Text>
          <Button size="sm" variant="ghost" onPress={discardFailedUploads}>
            <Text className="font-sans-semibold">Descartar</Text>
          </Button>
          <Button size="sm" variant="outline" onPress={retryFailedUploads}>
            <Text className="font-sans-semibold">Reintentar</Text>
          </Button>
        </View>
      )}
    </View>
  );
}
