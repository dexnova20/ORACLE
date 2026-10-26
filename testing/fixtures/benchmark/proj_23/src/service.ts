// import { broken } from "./missing_submodule";
/* import { fatal } from "../nonexistent_module"; */
import { compute } from "./helper";

export function executeService(): string {
  // Notice: import fake from "./fake_module";
  return compute();
}
