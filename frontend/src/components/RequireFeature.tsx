import type { ReactNode } from 'react';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { FeatureFlags } from '@/types/pos';
import FeatureUnavailable from './FeatureUnavailable';

export default function RequireFeature({
  flag,
  children,
}: {
  flag: keyof FeatureFlags;
  children: ReactNode;
}) {
  const enabled = useFeatureFlagStore((s) => s.flags[flag]);
  const loaded = useFeatureFlagStore((s) => s.flagsLoaded);

  // Flags load asynchronously. Before they arrive, render children (fail-open)
  // so enabled features don't briefly flash "unavailable".
  if (!loaded) return <>{children}</>;
  if (!enabled) return <FeatureUnavailable flag={flag} />;
  return <>{children}</>;
}
