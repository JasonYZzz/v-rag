"use client";

import type { Node } from "@xyflow/react";

import type { FlowNodeData } from "@/lib/flow-graph";
import type { JsonSchema } from "@/lib/orchestration-store";
import { filterConfigBySchema, useOrchestrationStore } from "@/lib/orchestration-store";

type ParamFormProps = {
  node: Node<FlowNodeData> | null;
  schema: JsonSchema | null;
};

export function NodeParamForm({ node, schema }: ParamFormProps) {
  const patchNodeConfig = useOrchestrationStore((state) => state.patchNodeConfig);
  if (!node) {
    return <p className="text-sm text-muted">Select a node to edit parameters.</p>;
  }
  const properties = schema?.properties ?? {};
  const entries = Object.entries(properties);
  if (!schema || entries.length === 0) {
    return (
      <section className="rounded-[8px] border border-border bg-bg p-3">
        <h2 className="text-sm font-semibold">{node.data.nodeType}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">This node has no editable P1 parameters.</p>
      </section>
    );
  }
  return (
    <section className="space-y-3 rounded-[8px] border border-border bg-bg p-3">
      <h2 className="text-sm font-semibold">Parameters</h2>
      {entries.map(([key, property]) => {
        const value = node.data.config[key] ?? property.default ?? "";
        const id = `${node.id}-${key}`;
        return (
          <label key={key} htmlFor={id} className="block space-y-1.5">
            <span className="text-xs font-medium text-muted">{property.title ?? key}</span>
            {property.enum ? (
              <select
                id={id}
                className="h-9 w-full rounded-[8px] border border-border bg-surface px-2 text-sm"
                value={String(value)}
                onChange={(event) =>
                  patchNodeConfig(node.id, filterConfigBySchema({ [key]: event.target.value }, schema), schema)
                }
              >
                {property.enum.map((option) => (
                  <option key={String(option)} value={String(option)}>
                    {String(option)}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id={id}
                type={property.type === "integer" || property.type === "number" ? "number" : "text"}
                min={property.minimum}
                max={property.maximum}
                className="h-9 w-full rounded-[8px] border border-border bg-surface px-2 text-sm"
                value={String(value)}
                onChange={(event) => {
                  const nextValue =
                    property.type === "integer" || property.type === "number"
                      ? Number(event.target.value)
                      : event.target.value;
                  patchNodeConfig(node.id, filterConfigBySchema({ [key]: nextValue }, schema), schema);
                }}
              />
            )}
            {property.description ? (
              <span className="block text-xs leading-5 text-muted">{property.description}</span>
            ) : null}
          </label>
        );
      })}
    </section>
  );
}
