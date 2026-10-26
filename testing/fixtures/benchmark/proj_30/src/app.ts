import lodash from "lodash";

export function chunkArray<T>(items: T[], size: number): T[][] {
  return lodash.chunk(items, size);
}
