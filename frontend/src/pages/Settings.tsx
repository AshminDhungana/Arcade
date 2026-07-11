import { useState } from 'react';
import { Tabs, type TabItem } from '@/components/ui/Tabs';
import { Flag, Tag, Clock, Users, Utensils, Printer } from 'lucide-react';
import { FeatureFlagsTab } from '@/components/settings/FeatureFlagsTab';
import { PricingTab } from '@/components/settings/PricingTab';
import { SchedulesTab } from '@/components/settings/SchedulesTab';
import { StaffTab } from '@/components/settings/StaffTab';
import { MenuTab } from '@/components/settings/MenuTab';
import { PrinterTab } from '@/components/settings/PrinterTab';

const TABS: TabItem[] = [
  { id: 'flags', label: 'Feature Flags', icon: <Flag className="h-4 w-4" /> },
  { id: 'pricing', label: 'Pricing', icon: <Tag className="h-4 w-4" /> },
  { id: 'schedules', label: 'Schedules', icon: <Clock className="h-4 w-4" /> },
  { id: 'staff', label: 'Staff', icon: <Users className="h-4 w-4" /> },
  { id: 'menu', label: 'Menu', icon: <Utensils className="h-4 w-4" /> },
  { id: 'printer', label: 'Printer', icon: <Printer className="h-4 w-4" /> },
];

export default function SettingsPage() {
  const [active, setActive] = useState('flags');

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200">
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-700 bg-slate-800/95 px-6 py-4 backdrop-blur">
        <h1 className="text-xl font-bold text-white">Settings</h1>
      </header>
      <Tabs tabs={TABS} active={active} onChange={setActive} />
      <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
        {active === 'flags' && <FeatureFlagsTab />}
        {active === 'pricing' && <PricingTab />}
        {active === 'schedules' && <SchedulesTab />}
        {active === 'staff' && <StaffTab />}
        {active === 'menu' && <MenuTab />}
        {active === 'printer' && <PrinterTab />}
      </main>
    </div>
  );
}
