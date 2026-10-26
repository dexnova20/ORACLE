import { formatDate } from "./utils";

export function getFormattedNow(): string {
  return formatDate(new Date());
}
