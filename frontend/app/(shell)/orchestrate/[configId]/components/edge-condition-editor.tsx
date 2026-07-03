"use client";

import { intentValues, makeCondition } from "@/lib/flow-graph";
import { isAllowedCondition } from "@/lib/orchestration-store";

type EdgeConditionEditorProps = {
  value: string | null;
  onChange: (condition: string | null) => void;
};

export function EdgeConditionEditor({ value, onChange }: EdgeConditionEditorProps) {
  const currentValue = value?.split("=")[1] ?? "";
  return (
    <section className="space-y-3 rounded-[8px] border border-border bg-bg p-3">
      <h2 className="text-sm font-semibold">Condition</h2>
      <label className="block space-y-1.5">
        <span className="text-xs font-medium text-muted">Field</span>
        <select className="h-9 w-full rounded-[8px] border border-border bg-surface px-2 text-sm" value="intent" disabled>
          <option value="intent">intent</option>
        </select>
      </label>
      <label className="block space-y-1.5">
        <span className="text-xs font-medium text-muted">Value</span>
        <select
          className="h-9 w-full rounded-[8px] border border-border bg-surface px-2 text-sm"
          value={currentValue}
          onChange={(event) => {
            const condition = makeCondition(event.target.value as (typeof intentValues)[number]);
            onChange(isAllowedCondition(condition) ? condition : null);
          }}
        >
          <option value="">Always</option>
          {intentValues.map((intent) => (
            <option key={intent} value={intent}>
              {intent}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}
