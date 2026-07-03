import { ConfigView } from "@/components/config/config-view";

export default function ConfigPage() {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold">Config</h1>
        <p className="mt-1 text-sm text-muted">Inspect provider, storage, and runtime settings.</p>
      </header>
      <ConfigView />
    </div>
  );
}
