import { sendRequest } from "./missing_transport";

export function handleRequest(): void {
  sendRequest("payload");
}
