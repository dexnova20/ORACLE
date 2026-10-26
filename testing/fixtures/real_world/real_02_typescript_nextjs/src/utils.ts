export function formatCurrency(amount: number): string {
  return "$" + amount.toFixed(2);
}

export function sanitizeInput(input: string): string {
  return input.trim();
}
