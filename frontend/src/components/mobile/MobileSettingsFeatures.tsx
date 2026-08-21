import { useState } from 'react'
import type { MobileSettings } from '@/hooks/useSettings'

interface MobileSettingsFeaturesProps {
  settings: MobileSettings
  onChange: (data: Partial<MobileSettings>) => void
}

export function MobileSettingsFeatures({ settings, onChange }: MobileSettingsFeaturesProps) {
  const [enableMembers, setEnableMembers] = useState(settings.enableMembers)
  const [enableTournaments, setEnableTournaments] = useState(settings.enableTournaments)

  const handleSave = () => {
    onChange({ enableMembers, enableTournaments })
  }

  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="mobile-settings-features" aria-labelledby="features-heading">
      <h2 id="features-heading" className="px-4 py-3 text-base font-semibold text-gray-900 border-b border-gray-200">
        Features
      </h2>
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-gray-900">Members Management</div>
            <div className="text-sm text-gray-500">Enable member registration and loyalty</div>
          </div>
<label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={enableMembers}
                onChange={(e) => setEnableMembers(e.target.checked)}
                className="sr-only peer"
                aria-label="Enable Members Management"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-gray-900">Tournaments</div>
            <div className="text-sm text-gray-500">Enable tournament brackets and events</div>
          </div>
<label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={enableTournaments}
                onChange={(e) => setEnableTournaments(e.target.checked)}
                className="sr-only peer"
                aria-label="Enable Tournaments"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
        </div>
        <button
          onClick={handleSave}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium touch-target-min"
        >
          Save Feature Settings
        </button>
      </div>
    </section>
  )
}
