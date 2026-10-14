import { Tabs } from 'expo-router';
import { CalendarDaysIcon, ShirtIcon, SparklesIcon, WandSparklesIcon } from 'lucide-react-native';

import { Icon } from '@/components/ui/icon';

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Hoy',
          tabBarIcon: ({ color, size }) => <Icon as={SparklesIcon} color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="closet"
        options={{
          title: 'Armario',
          tabBarIcon: ({ color, size }) => <Icon as={ShirtIcon} color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="inspire"
        options={{
          title: 'Inspira',
          tabBarIcon: ({ color, size }) => <Icon as={WandSparklesIcon} color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: 'Calendario',
          tabBarIcon: ({ color, size }) => <Icon as={CalendarDaysIcon} color={color} size={size} />,
        }}
      />
    </Tabs>
  );
}
