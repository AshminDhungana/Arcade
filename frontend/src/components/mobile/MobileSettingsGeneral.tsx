import { useState } from 'react'
import type { MobileSettings } from '@/hooks/useSettings'

interface MobileSettingsGeneralProps {
  settings: MobileSettings
  onChange: (data: Partial<MobileSettings>) => void
}

export function MobileSettingsGeneral({ settings, onChange }: MobileSettingsGeneralProps) {
  const [cafeName, setCafeName] = useState(settings.cafeName)
  const [timezone, setTimezone] = useState(settings.timezone)
  const [currency, setCurrency] = useState(settings.currency)
  const [autoCloseShift, setAutoCloseShift] = useState(settings.autoCloseShift)
  const [sessionTimeout, setSessionTimeout] = useState(settings.sessionTimeout)

  const handleSave = () => {
    onChange({ cafeName, timezone, currency, autoCloseShift, sessionTimeout })
  }

  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="mobile-settings-general" aria-labelledby="general-heading">
      <h2 id="general-heading" className="px-4 py-3 text-base font-semibold text-gray-900 border-b border-gray-200">
        General
      </h2>
      <div className="p-4 space-y-4">
        <div>
          <label htmlFor="cafe-name" className="block text-sm font-medium text-gray-700 mb-1">Cafe Name</label>
          <input
            id="cafe-name"
            type="text"
            value={cafeName}
            onChange={(e) => setCafeName(e.target.value)}
            className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-base touch-target-min"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="timezone" className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
            <select
              id="timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-base touch-target-min"
            >
              <option value="Asia/Kolkata">Asia/Kolkata</option>
              <option value="UTC">UTC</option>
              <option value="America/New_York">America/New_York</option>
              <option value="Europe/London">Europe/London</option>
            </select>
          </div>
          <div>
            <label htmlFor="currency" className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
            <select
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-base touch-target-min"
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="session-timeout" className="block text-sm font-medium text-gray-700 mb-1">Session Timeout (min)</label>
            <input
              id="session-timeout"
              type="number"
              value={sessionTimeout}
              onChange={(e) => setSessionTimeout(Number(e.target.value))}
              min="1"
              max="1440"
              className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-base touch-target-min"
            />
          </div>
          <div className="flex items-center justify-between pt-6">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={autoCloseShift}
                onChange={(e) => setAutoCloseShift(e.target.checked)}
                className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Auto-close shift at midnight</span>
            </label>
          </div>
        </div>
        <button
          onClick={handleSave}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium touch-target-min"
        >
          Save General Settings
        </button>
      </div>
    </section>
  )
}
