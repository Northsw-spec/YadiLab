export function deepCloneJson<T>(value: T): T {
  if (Array.isArray(value)) return value.map((x) => deepCloneJson(x)) as T;
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (v !== undefined) out[k] = deepCloneJson(v);
    }
    return out as T;
  }
  return value;
}

export function deepMergeObjects(
  base: Readonly<Record<string, unknown>>,
  override: Readonly<Record<string, unknown>>,
): Readonly<Record<string, unknown>> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(base)) out[k] = deepCloneJson(v);
  for (const [k, v] of Object.entries(override)) {
    const current = out[k];
    if (
      current !== null && typeof current === "object" && !Array.isArray(current) &&
      v !== null && typeof v === "object" && !Array.isArray(v)
    ) {
      out[k] = deepMergeObjects(current as Record<string, unknown>, v as Record<string, unknown>);
    } else {
      out[k] = deepCloneJson(v);
    }
  }
  return out;
}

export function sortedUniqueStrings(values: readonly string[]): readonly string[] {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b, "en"));
}
