import _ from "lodash";

export function formatKeys(obj: Record<string, unknown>): string[] {
  return _.keys(obj);
}
