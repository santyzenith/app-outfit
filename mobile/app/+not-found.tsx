import { Link, Stack } from 'expo-router';
import { View } from 'react-native';

import { Button } from '@/components/app/button';
import { Text } from '@/components/ui/text';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'No encontrada' }} />
      <View className="flex-1 items-center justify-center gap-4 bg-background px-8">
        <Text className="text-center font-sans-semibold text-lg">Esta pantalla no existe</Text>
        <Link href="/" asChild>
          <Button>
            <Text className="font-sans-semibold">Volver al inicio</Text>
          </Button>
        </Link>
      </View>
    </>
  );
}
