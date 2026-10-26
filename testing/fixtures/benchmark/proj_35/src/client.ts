import { send } from "./missing_sender";

export function dispatch(): void {
  send("data");
}
