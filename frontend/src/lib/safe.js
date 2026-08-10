/** Always return an array. Never pass error objects / null into .map(). */
export function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object") {
    if (Array.isArray(value.items)) return value.items;
    if (Array.isArray(value.data)) return value.data;
    if (Array.isArray(value.results)) return value.results;
  }
  return [];
}
