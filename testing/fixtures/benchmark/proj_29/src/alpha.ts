import { getBeta } from "./beta";

export function getAlpha(): string {
  return "alpha-" + getBeta();
}
