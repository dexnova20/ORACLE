import { appConfig } from "@/config/settings";

export function getPort(): number {
  return appConfig.port;
}
