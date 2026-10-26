import { formatCurrency, sanitizeInput } from "./utils";

export function renderSummary(name: string, balance: number): string {
  const cleanName = sanitizeInput(name);
  const formattedBalance = formatCurrency(balance);
  return `${cleanName}: ${formattedBalance}`;
}
