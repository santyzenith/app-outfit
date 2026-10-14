import * as Haptics from 'expo-haptics';

// Vibration is a nicety: a phone without it must never see an error.
function safely(run: () => Promise<void>): void {
  run().catch(() => undefined);
}

export function tapFeedback(): void {
  safely(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light));
}

export function selectionFeedback(): void {
  safely(() => Haptics.selectionAsync());
}

export function successFeedback(): void {
  safely(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success));
}
