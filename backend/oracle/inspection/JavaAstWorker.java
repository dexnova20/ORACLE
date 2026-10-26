package oracle.inspection;

import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.tools.*;
import java.io.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * Isolated Java AST Worker for ORACLE.
 *
 * Uses OpenJDK's official Compiler Tree API (JavacTask / com.sun.source.tree)
 * to parse Java source text inertly without compiling or executing target code.
 *
 * Communicates via stdin/stdout using JSON streaming.
 */
public class JavaAstWorker {

    static class StringSourceJavaObject extends SimpleJavaFileObject {
        final String content;

        StringSourceJavaObject(String name, String content) {
            super(URI.create("string:///" + name.replace("\\", "/")), Kind.SOURCE);
            this.content = content;
        }

        @Override
        public CharSequence getCharContent(boolean ignoreEncodingErrors) {
            return content;
        }
    }

    // --- Minimal Robust JSON Parser ---
    static class JsonValue {
        Object val;
        JsonValue(Object val) { this.val = val; }
        @SuppressWarnings("unchecked")
        Map<String, JsonValue> asObj() { return (Map<String, JsonValue>) val; }
        @SuppressWarnings("unchecked")
        List<JsonValue> asList() { return (List<JsonValue>) val; }
        String asString() { return (String) val; }
    }

    static class JsonParser {
        final String src;
        int pos = 0;

        JsonParser(String src) { this.src = src; }

        void skipWhitespace() {
            while (pos < src.length() && Character.isWhitespace(src.charAt(pos))) pos++;
        }

        JsonValue parse() {
            skipWhitespace();
            if (pos >= src.length()) return null;
            char c = src.charAt(pos);
            if (c == '{') return parseObject();
            if (c == '[') return parseArray();
            if (c == '"') return parseString();
            if (c == 't' || c == 'f') return parseBool();
            if (c == 'n') return parseNull();
            return parseNumber();
        }

        JsonValue parseObject() {
            pos++; // '{'
            Map<String, JsonValue> map = new LinkedHashMap<>();
            while (pos < src.length()) {
                skipWhitespace();
                if (pos >= src.length() || src.charAt(pos) == '}') { pos++; break; }
                if (src.charAt(pos) == ',') { pos++; skipWhitespace(); }
                if (pos >= src.length() || src.charAt(pos) == '}') { pos++; break; }
                String key = parseString().asString();
                skipWhitespace();
                if (pos < src.length() && src.charAt(pos) == ':') pos++;
                JsonValue val = parse();
                map.put(key, val);
            }
            return new JsonValue(map);
        }

        JsonValue parseArray() {
            pos++; // '['
            List<JsonValue> list = new ArrayList<>();
            while (pos < src.length()) {
                skipWhitespace();
                if (pos >= src.length() || src.charAt(pos) == ']') { pos++; break; }
                if (src.charAt(pos) == ',') { pos++; skipWhitespace(); }
                if (pos >= src.length() || src.charAt(pos) == ']') { pos++; break; }
                list.add(parse());
            }
            return new JsonValue(list);
        }

        JsonValue parseString() {
            pos++; // opening '"'
            StringBuilder sb = new StringBuilder();
            while (pos < src.length()) {
                char c = src.charAt(pos++);
                if (c == '"') break;
                if (c == '\\' && pos < src.length()) {
                    char esc = src.charAt(pos++);
                    if (esc == '"') sb.append('"');
                    else if (esc == '\\') sb.append('\\');
                    else if (esc == '/') sb.append('/');
                    else if (esc == 'b') sb.append('\b');
                    else if (esc == 'f') sb.append('\f');
                    else if (esc == 'n') sb.append('\n');
                    else if (esc == 'r') sb.append('\r');
                    else if (esc == 't') sb.append('\t');
                    else if (esc == 'u' && pos + 4 <= src.length()) {
                        sb.append((char) Integer.parseInt(src.substring(pos, pos + 4), 16));
                        pos += 4;
                    } else sb.append(esc);
                } else {
                    sb.append(c);
                }
            }
            return new JsonValue(sb.toString());
        }

        JsonValue parseBool() {
            if (src.startsWith("true", pos)) { pos += 4; return new JsonValue(Boolean.TRUE); }
            if (src.startsWith("false", pos)) { pos += 5; return new JsonValue(Boolean.FALSE); }
            return null;
        }

        JsonValue parseNull() {
            if (src.startsWith("null", pos)) { pos += 4; return new JsonValue(null); }
            return null;
        }

        JsonValue parseNumber() {
            int start = pos;
            if (pos < src.length() && src.charAt(pos) == '-') pos++;
            while (pos < src.length() && (Character.isDigit(src.charAt(pos)) || src.charAt(pos) == '.' || src.charAt(pos) == 'e' || src.charAt(pos) == 'E' || src.charAt(pos) == '+' || src.charAt(pos) == '-')) pos++;
            String num = src.substring(start, pos);
            return new JsonValue(num.contains(".") ? Double.parseDouble(num) : Long.parseLong(num));
        }
    }

    // --- JSON Serialization Helpers ---
    static String escapeJson(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder();
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\b': sb.append("\\b"); break;
                case '\f': sb.append("\\f"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 32) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append('"');
        return sb.toString();
    }

    static class TypeInfo {
        String name;
        String kind;
        boolean isNested;
        List<String> modifiers = new ArrayList<>();
        long line;
        long column;
        long offset;
    }

    static class ImportInfo {
        String name;
        boolean isStatic;
        boolean isWildcard;
        long line;
        long column;
        long offset;
    }

    static class DiagnosticInfo {
        String message;
        long line;
        long column;
        long offset;
    }

    static class ParsedFileResult {
        String path;
        String packageName;
        long packageLine;
        List<ImportInfo> imports = new ArrayList<>();
        List<TypeInfo> declaredTypes = new ArrayList<>();
        List<DiagnosticInfo> syntaxErrors = new ArrayList<>();
        int lineCount = 0;
    }

    public static void main(String[] args) {
        try {
            // Read all input from stdin
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int r;
            while ((r = System.in.read(buf)) != -1) {
                baos.write(buf, 0, r);
            }
            String rawJson = baos.toString(StandardCharsets.UTF_8);

            if (rawJson.trim().isEmpty()) {
                System.out.println("{\"files\":[]}");
                return;
            }

            JsonValue root = new JsonParser(rawJson).parse();
            if (root == null || root.asObj() == null || !root.asObj().containsKey("files")) {
                System.out.println("{\"error\": \"Invalid input: missing 'files' array\", \"files\": []}");
                return;
            }

            List<JsonValue> fileItems = root.asObj().get("files").asList();
            if (fileItems == null || fileItems.isEmpty()) {
                System.out.println("{\"files\":[]}");
                return;
            }

            JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
            if (compiler == null) {
                System.out.println("{\"error\": \"System JavaCompiler is not available in current JVM runtime\", \"files\": []}");
                return;
            }

            DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
            StandardJavaFileManager fm = compiler.getStandardFileManager(diagnostics, null, StandardCharsets.UTF_8);

            Map<String, String> fileContents = new LinkedHashMap<>();
            List<JavaFileObject> compilationUnits = new ArrayList<>();

            for (JsonValue item : fileItems) {
                Map<String, JsonValue> obj = item.asObj();
                String path = obj.get("path").asString();
                String content = obj.containsKey("content") && obj.get("content").val != null ? obj.get("content").asString() : "";
                fileContents.put(path, content);
                compilationUnits.add(new StringSourceJavaObject(path, content));
            }

            // Execute AST parse only (zero compilation / zero code execution)
            JavacTask task = (JavacTask) compiler.getTask(null, fm, diagnostics, null, null, compilationUnits);
            Iterable<? extends CompilationUnitTree> trees = task.parse();
            SourcePositions sp = Trees.instance(task).getSourcePositions();

            Map<String, ParsedFileResult> resultsByPath = new LinkedHashMap<>();
            for (String path : fileContents.keySet()) {
                ParsedFileResult res = new ParsedFileResult();
                res.path = path;
                String content = fileContents.get(path);
                res.lineCount = content.isEmpty() ? 0 : content.split("\r\n|\r|\n", -1).length;
                resultsByPath.put(path, res);
            }

            // Extract AST elements
            for (CompilationUnitTree tree : trees) {
                String uriStr = tree.getSourceFile().getName();
                String cleanPath = uriStr.replace("string:///", "").replace("\\", "/");
                // Find matching result entry
                ParsedFileResult res = resultsByPath.get(cleanPath);
                if (res == null) {
                    for (String key : resultsByPath.keySet()) {
                        if (cleanPath.endsWith(key) || key.endsWith(cleanPath)) {
                            res = resultsByPath.get(key);
                            break;
                        }
                    }
                }
                if (res == null) {
                    res = new ParsedFileResult();
                    res.path = cleanPath;
                    resultsByPath.put(cleanPath, res);
                }

                // Package declaration
                if (tree.getPackage() != null) {
                    res.packageName = tree.getPackage().getPackageName().toString();
                    long pPos = sp.getStartPosition(tree, tree.getPackage());
                    if (tree.getLineMap() != null && pPos != Diagnostic.NOPOS) {
                        res.packageLine = tree.getLineMap().getLineNumber(pPos);
                    }
                }

                // Import declarations
                for (ImportTree imp : tree.getImports()) {
                    ImportInfo info = new ImportInfo();
                    info.name = imp.getQualifiedIdentifier().toString();
                    info.isStatic = imp.isStatic();
                    info.isWildcard = info.name.endsWith(".*");
                    long pos = sp.getStartPosition(tree, imp);
                    if (tree.getLineMap() != null && pos != Diagnostic.NOPOS) {
                        info.line = tree.getLineMap().getLineNumber(pos);
                        info.column = tree.getLineMap().getColumnNumber(pos);
                        info.offset = pos;
                    }
                    res.imports.add(info);
                }

                // Type declarations
                for (Tree typeDecl : tree.getTypeDecls()) {
                    if (typeDecl instanceof ClassTree ct) {
                        extractType(tree, ct, sp, false, res.declaredTypes);
                    }
                }
            }

            // Collect syntax errors
            for (Diagnostic<? extends JavaFileObject> diag : diagnostics.getDiagnostics()) {
                if (diag.getKind() == Diagnostic.Kind.ERROR) {
                    DiagnosticInfo dInfo = new DiagnosticInfo();
                    dInfo.message = diag.getMessage(Locale.ROOT);
                    dInfo.line = diag.getLineNumber();
                    dInfo.column = diag.getColumnNumber();
                    dInfo.offset = diag.getPosition();

                    String diagPath = "";
                    if (diag.getSource() != null) {
                        diagPath = diag.getSource().getName().replace("string:///", "").replace("\\", "/");
                    }

                    ParsedFileResult targetRes = resultsByPath.get(diagPath);
                    if (targetRes == null) {
                        for (String key : resultsByPath.keySet()) {
                            if (diagPath.endsWith(key) || key.endsWith(diagPath)) {
                                targetRes = resultsByPath.get(key);
                                break;
                            }
                        }
                    }
                    if (targetRes != null) {
                        targetRes.syntaxErrors.add(dInfo);
                    } else if (!resultsByPath.isEmpty()) {
                        resultsByPath.values().iterator().next().syntaxErrors.add(dInfo);
                    }
                }
            }

            // Output JSON
            StringBuilder out = new StringBuilder();
            out.append("{\"files\":[");
            boolean firstFile = true;
            for (ParsedFileResult fr : resultsByPath.values()) {
                if (!firstFile) out.append(",");
                firstFile = false;
                out.append("{");
                out.append("\"path\":").append(escapeJson(fr.path)).append(",");
                out.append("\"package_name\":").append(escapeJson(fr.packageName)).append(",");
                out.append("\"package_line\":").append(fr.packageLine).append(",");
                out.append("\"line_count\":").append(fr.lineCount).append(",");

                // Imports
                out.append("\"imports\":[");
                boolean firstImp = true;
                for (ImportInfo ii : fr.imports) {
                    if (!firstImp) out.append(",");
                    firstImp = false;
                    out.append("{");
                    out.append("\"name\":").append(escapeJson(ii.name)).append(",");
                    out.append("\"is_static\":").append(ii.isStatic).append(",");
                    out.append("\"is_wildcard\":").append(ii.isWildcard).append(",");
                    out.append("\"line\":").append(ii.line).append(",");
                    out.append("\"column\":").append(ii.column).append(",");
                    out.append("\"offset\":").append(ii.offset);
                    out.append("}");
                }
                out.append("],");

                // Declared types
                out.append("\"declared_types\":[");
                boolean firstType = true;
                for (TypeInfo ti : fr.declaredTypes) {
                    if (!firstType) out.append(",");
                    firstType = false;
                    out.append("{");
                    out.append("\"name\":").append(escapeJson(ti.name)).append(",");
                    out.append("\"kind\":").append(escapeJson(ti.kind)).append(",");
                    out.append("\"is_nested\":").append(ti.isNested).append(",");
                    out.append("\"line\":").append(ti.line).append(",");
                    out.append("\"column\":").append(ti.column).append(",");
                    out.append("\"offset\":").append(ti.offset).append(",");
                    out.append("\"modifiers\":[");
                    boolean firstMod = true;
                    for (String m : ti.modifiers) {
                        if (!firstMod) out.append(",");
                        firstMod = false;
                        out.append(escapeJson(m));
                    }
                    out.append("]");
                    out.append("}");
                }
                out.append("],");

                // Syntax errors
                out.append("\"syntax_errors\":[");
                boolean firstErr = true;
                for (DiagnosticInfo di : fr.syntaxErrors) {
                    if (!firstErr) out.append(",");
                    firstErr = false;
                    out.append("{");
                    out.append("\"message\":").append(escapeJson(di.message)).append(",");
                    out.append("\"line\":").append(di.line).append(",");
                    out.append("\"column\":").append(di.column).append(",");
                    out.append("\"offset\":").append(di.offset);
                    out.append("}");
                }
                out.append("]");

                out.append("}");
            }
            out.append("]}");

            System.out.println(out.toString());

        } catch (Exception ex) {
            String msg = ex.getMessage() != null ? ex.getMessage() : ex.toString();
            System.out.println("{\"error\":" + escapeJson(msg) + ",\"files\":[]}");
        }
    }

    static void extractType(
        CompilationUnitTree tree,
        ClassTree ct,
        SourcePositions sp,
        boolean isNested,
        List<TypeInfo> outList
    ) {
        TypeInfo ti = new TypeInfo();
        ti.name = ct.getSimpleName().toString();
        ti.isNested = isNested;

        Tree.Kind kind = ct.getKind();
        if (kind == Tree.Kind.INTERFACE) {
            ti.kind = "interface";
        } else if (kind == Tree.Kind.ENUM) {
            ti.kind = "enum";
        } else if (kind == Tree.Kind.RECORD) {
            ti.kind = "record";
        } else if (kind == Tree.Kind.ANNOTATION_TYPE) {
            ti.kind = "annotation";
        } else {
            ti.kind = "class";
        }

        ModifiersTree mods = ct.getModifiers();
        if (mods != null && mods.getFlags() != null) {
            for (javax.lang.model.element.Modifier m : mods.getFlags()) {
                ti.modifiers.add(m.name().toLowerCase(Locale.ROOT));
            }
        }

        long pos = sp.getStartPosition(tree, ct);
        if (tree.getLineMap() != null && pos != Diagnostic.NOPOS) {
            ti.line = tree.getLineMap().getLineNumber(pos);
            ti.column = tree.getLineMap().getColumnNumber(pos);
            ti.offset = pos;
        }

        if (ti.name != null && !ti.name.isEmpty()) {
            outList.add(ti);
        }

        for (Tree member : ct.getMembers()) {
            if (member instanceof ClassTree innerCt) {
                extractType(tree, innerCt, sp, true, outList);
            }
        }
    }
}
