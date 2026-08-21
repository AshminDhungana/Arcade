import { useSettings } from '@/hooks/useSettings'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useEffect } from 'react'
import { MobileSettingsGeneral } from '@/components/mobile/MobileSettingsGeneral'
import { MobileSettingsFeatures } from '@/components/mobile/MobileSettingsFeatures'
import { MobileSettingsPrinter } from '@/components/mobile/MobileSettingsPrinter'
import { MobileSettingsSaveButton } from '@/components/mobile/MobileSettingsSaveButton'

export function MobileSettings() {
  const { data: settings, refetch, mutate } = useSettings()
  const { subscribe } = useWebSocket()

  useEffect(() => {
    const unsubscribe = subscribe('settings', () => refetch())
    return unsubscribe
  }, [subscribe, refetch])

  if (!settings) {
    return (
      <div className="min-h-[400px] flex items-center justify-center" data-testid="mobile-settings-loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div data-testid="mobile-settings" className="space-y-4">
      <MobileSettingsGeneral settings={settings} onChange={mutate} />
      <MobileSettingsFeatures settings={settings} onChange={mutate} />
      <MobileSettingsPrinter settings={settings} onChange={mutate} />
      <MobileSettingsSaveButton onSave={mutate} />
    </div>
  )
}
