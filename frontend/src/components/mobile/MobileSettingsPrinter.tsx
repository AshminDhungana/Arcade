import { useState } from 'react'
import type { MobileSettings } from '@/hooks/useSettings'

interface MobileSettingsPrinterProps {
  settings: MobileSettings
  onChange: (data: Partial<MobileSettings>) => void
}

export function MobileSettingsPrinter({ settings, onChange }: MobileSettingsPrinterProps) {
  const [printerEnabled, setPrinterEnabled] = useState(settings.printerEnabled)
  const [printerIp, setPrinterIp] = useState(settings.printerIp)

  const handleSave = () => {
    onChange({ printerEnabled, printerIp })
  }

  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="mobile-settings-printer" aria-labelledby="printer-heading">
      <h2 id="printer-heading" className="px-4 py-3 text-base font-semibold text-gray-900 border-b border-gray-200">
        Printer
      </h2>
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-gray-900">Receipt Printer</div>
            <div className="text-sm text-gray-500">Enable thermal receipt printing</div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={printerEnabled}
              onChange={(e) => setPrinterEnabled(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>
        {printerEnabled && (
          <div>
            <label htmlFor="printer-ip" className="block text-sm font-medium text-gray-700 mb-1">Printer IP Address</label>
            <input
              id="printer-ip"
              type="text"
              value={printerIp}
              onChange={(e) => setPrinterIp(e.target.value)}
              placeholder="192.168.1.100"
              className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-base touch-target-min"
            />
          </div>
        )}
        <button
          onClick={handleSave}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium touch-target-min"
        >
          Save Printer Settings
        </button>
      </div>
    </section>
  )
}
