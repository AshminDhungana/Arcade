interface MobileSettingsSaveButtonProps {
  onSave: (data: Partial<import('@/hooks/useSettings').MobileSettings>) => void
}

export function MobileSettingsSaveButton({ onSave }: MobileSettingsSaveButtonProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4" data-testid="mobile-settings-save">
      <button
        onClick={() => onSave({})}
        className="w-full bg-green-600 text-white py-3 rounded-lg font-medium touch-target-min"
      >
        Save All Settings
      </button>
    </div>
  )
}
