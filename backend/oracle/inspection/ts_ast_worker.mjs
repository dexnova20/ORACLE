/**
 * Pure static TypeScript / JavaScript AST worker for ORACLE.
 *
 * Uses the official TypeScript Compiler API (ts.createSourceFile) to parse
 * source code into an abstract syntax tree without executing target code.
 *
 * Output: JSON structured summaries including file status, line counts,
 * parse diagnostics (syntax errors), and extracted import/export declarations.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);

function findTypeScript() {
  if (process.env.TYPESCRIPT_PATH) {
    try {
      return require(process.env.TYPESCRIPT_PATH);
    } catch (_) {}
  }
  // Try standard Node resolution
  try {
    return require("typescript");
  } catch (_) {}
  // Try frontend node_modules from repo root
  try {
    const fromCwd = path.resolve(process.cwd(), "frontend/node_modules/typescript");
    return require(fromCwd);
  } catch (_) {}
  // Try relative from backend/oracle/inspection/
  try {
    const fromDir = path.resolve(__dirname, "../../../frontend/node_modules/typescript");
    return require(fromDir);
  } catch (_) {}
  throw new Error("TypeScript compiler package could not be resolved.");
}

const ts = findTypeScript();

function getScriptKind(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".ts":
    case ".mts":
    case ".cts":
      return ts.ScriptKind.TS;
    case ".tsx":
      return ts.ScriptKind.TSX;
    case ".js":
    case ".mjs":
    case ".cjs":
      return ts.ScriptKind.JS;
    case ".jsx":
      return ts.ScriptKind.JSX;
    case ".json":
      return ts.ScriptKind.JSON;
    default:
      return ts.ScriptKind.Unknown;
  }
}

function parseFileRecord(relPath, content) {
  const scriptKind = getScriptKind(relPath);
  const lineCount = content ? content.split(/\r?\n/).length : 0;

  let sf;
  try {
    sf = ts.createSourceFile(
      relPath,
      content,
      ts.ScriptTarget.Latest,
      true, // setParentNodes
      scriptKind
    );
  } catch (err) {
    return {
      file_path: relPath,
      status: "analysis_failed",
      line_count: lineCount,
      imports: [],
      syntax_error: {
        file_path: relPath,
        error_message: String(err && err.message ? err.message : err),
        line_number: 1,
        offset: 1,
      },
    };
  }

  // Check for parse diagnostics (syntax errors)
  if (sf.parseDiagnostics && sf.parseDiagnostics.length > 0) {
    const diag = sf.parseDiagnostics[0];
    const { line, character } = sf.getLineAndCharacterOfPosition(diag.start);
    const msg = ts.flattenDiagnosticMessageText(diag.messageText, "\n");
    return {
      file_path: relPath,
      status: "syntax_error",
      line_count: lineCount,
      imports: [],
      syntax_error: {
        file_path: relPath,
        error_message: msg,
        line_number: line + 1,
        offset: character + 1,
      },
    };
  }

  const imports = [];

  function visit(node) {
    // 1. ES import declaration: import ... from '...'
    if (ts.isImportDeclaration(node)) {
      const lineChar = sf.getLineAndCharacterOfPosition(node.getStart(sf));
      let specifier = "";
      if (node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
        specifier = node.moduleSpecifier.text;
      }

      const isTypeOnly = Boolean(node.importClause && node.importClause.isTypeOnly);
      const raw = node.getText(sf);
      const symbols = [];

      if (node.importClause) {
        if (node.importClause.name) {
          symbols.push({ name: node.importClause.name.text, kind: "default", isTypeOnly });
        }
        if (node.importClause.namedBindings) {
          if (ts.isNamedImports(node.importClause.namedBindings)) {
            for (const elem of node.importClause.namedBindings.elements) {
              symbols.push({
                name: elem.name.text,
                imported: elem.propertyName ? elem.propertyName.text : elem.name.text,
                isTypeOnly: Boolean(elem.isTypeOnly || isTypeOnly),
                kind: "named",
              });
            }
          } else if (ts.isNamespaceImport(node.importClause.namedBindings)) {
            symbols.push({
              name: node.importClause.namedBindings.name.text,
              kind: "namespace",
              isTypeOnly,
            });
          }
        }
      }

      if (specifier) {
        imports.push({
          specifier,
          raw_statement: raw,
          line_number: lineChar.line + 1,
          column_offset: lineChar.character + 1,
          import_kind: "import",
          is_type_only: isTypeOnly,
          symbols,
          is_computed: false,
        });
      }
    }
    // 2. Re-export declaration: export { x } from './foo'; export * from './bar';
    else if (ts.isExportDeclaration(node)) {
      if (node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
        const specifier = node.moduleSpecifier.text;
        const lineChar = sf.getLineAndCharacterOfPosition(node.getStart(sf));
        const raw = node.getText(sf);
        const isTypeOnly = Boolean(node.isTypeOnly);
        imports.push({
          specifier,
          raw_statement: raw,
          line_number: lineChar.line + 1,
          column_offset: lineChar.character + 1,
          import_kind: "export_from",
          is_type_only: isTypeOnly,
          symbols: [],
          is_computed: false,
        });
      }
    }
    // 3. Call expressions: require('...') or import('...')
    else if (ts.isCallExpression(node)) {
      // Dynamic import: import('./foo')
      if (node.expression.kind === ts.SyntaxKind.ImportKeyword && node.arguments.length >= 1) {
        const lineChar = sf.getLineAndCharacterOfPosition(node.getStart(sf));
        const raw = node.getText(sf);
        if (ts.isStringLiteral(node.arguments[0])) {
          imports.push({
            specifier: node.arguments[0].text,
            raw_statement: raw,
            line_number: lineChar.line + 1,
            column_offset: lineChar.character + 1,
            import_kind: "dynamic_import",
            is_type_only: false,
            symbols: [],
            is_computed: false,
          });
        } else {
          imports.push({
            specifier: node.arguments[0].getText(sf),
            raw_statement: raw,
            line_number: lineChar.line + 1,
            column_offset: lineChar.character + 1,
            import_kind: "unsupported_dynamic",
            is_type_only: false,
            symbols: [],
            is_computed: true,
          });
        }
      }
      // CommonJS require: require('./foo')
      else if (ts.isIdentifier(node.expression) && node.expression.text === "require" && node.arguments.length >= 1) {
        const lineChar = sf.getLineAndCharacterOfPosition(node.getStart(sf));
        const raw = node.getText(sf);
        if (ts.isStringLiteral(node.arguments[0])) {
          imports.push({
            specifier: node.arguments[0].text,
            raw_statement: raw,
            line_number: lineChar.line + 1,
            column_offset: lineChar.character + 1,
            import_kind: "require",
            is_type_only: false,
            symbols: [],
            is_computed: false,
          });
        } else {
          imports.push({
            specifier: node.arguments[0].getText(sf),
            raw_statement: raw,
            line_number: lineChar.line + 1,
            column_offset: lineChar.character + 1,
            import_kind: "unsupported_dynamic",
            is_type_only: false,
            symbols: [],
            is_computed: true,
          });
        }
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sf);

  return {
    file_path: relPath,
    status: "analyzed",
    line_count: lineCount,
    imports,
    syntax_error: null,
  };
}

async function main() {
  // Read all stdin
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const rawInput = Buffer.concat(chunks).toString("utf-8").trim();

  if (!rawInput) {
    process.stdout.write(JSON.stringify({ results: [], error: "No input provided" }));
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawInput);
  } catch (err) {
    process.stdout.write(JSON.stringify({ results: [], error: "Invalid JSON input: " + err.message }));
    return;
  }

  const results = [];
  const files = payload.files || [];
  const rootDir = payload.root_dir || "";

  for (const item of files) {
    const relPath = typeof item === "string" ? item : item.path;
    let content = typeof item === "object" && typeof item.content === "string" ? item.content : null;

    if (content === null && rootDir) {
      try {
        const fullPath = path.join(rootDir, relPath);
        content = fs.readFileSync(fullPath, "utf-8");
      } catch (err) {
        results.push({
          file_path: relPath,
          status: "analysis_failed",
          line_count: 0,
          imports: [],
          syntax_error: {
            file_path: relPath,
            error_message: "Could not read file: " + err.message,
            line_number: 1,
            offset: 1,
          },
        });
        continue;
      }
    }

    if (content === null) {
      content = "";
    }

    const res = parseFileRecord(relPath, content);
    results.push(res);
  }

  process.stdout.write(JSON.stringify({ results, error: null }));
}

main().catch((err) => {
  process.stderr.write("Worker error: " + err.stack + "\n");
  process.exit(1);
});
