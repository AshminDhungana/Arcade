import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { FeatureFlagsTab } from '@/components/settings/FeatureFlagsTab';
import { PricingTab } from '@/components/settings/PricingTab';
import { SchedulesTab } from '@/components/settings/SchedulesTab';
import { StaffTab } from '@/components/settings/StaffTab';
import { MenuTab } from '@/components/settings/MenuTab';
import { PrinterTab } from '@/components/settings/PrinterTab';

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-card/95 px-6 py-4 backdrop-blur">
        <h1 className="text-xl font-bold text-foreground">Settings</h1>
      </header>
      <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
        <Tabs defaultValue="flags" className="w-full">
          <TabsList>
            <TabsTrigger value="flags">Feature Flags</TabsTrigger>
            <TabsTrigger value="pricing">Pricing</TabsTrigger>
            <TabsTrigger value="schedules">Schedules</TabsTrigger>
            <TabsTrigger value="staff">Staff</TabsTrigger>
            <TabsTrigger value="menu">Menu</TabsTrigger>
            <TabsTrigger value="printer">Printer</TabsTrigger>
          </TabsList>
          <TabsContent value="flags"><FeatureFlagsTab /></TabsContent>
          <TabsContent value="pricing"><PricingTab /></TabsContent>
          <TabsContent value="schedules"><SchedulesTab /></TabsContent>
          <TabsContent value="staff"><StaffTab /></TabsContent>
          <TabsContent value="menu"><MenuTab /></TabsContent>
          <TabsContent value="printer"><PrinterTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
