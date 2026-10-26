import { execute } from "./executor";

export function runQuery(): string {
  const fakeImport = "import { evil } from './nowhere';";
  const templateLiteral = `import fake from "${fakeImport}"`;
  return execute(templateLiteral);
}
