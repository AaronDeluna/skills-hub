import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Ключи тест-кейсов (<КОД>-T<цифры>) в тест-методах - для разметки (markup-rules.md, разделы 2а и 6).
 *
 * java -Dfile.encoding=UTF-8 MarkupKeys.java missing <каталог тестов>...  - ключ есть, @TmsLink нет
 * java -Dfile.encoding=UTF-8 MarkupKeys.java dup <каталог тестов>...      - один ключ у разных тест-методов
 * java -Dfile.encoding=UTF-8 MarkupKeys.java count <каталог тестов>...    - сколько тест-методов и сколько с @TmsLink
 *
 * Учитываются только тест-методы: с @Test, @ParameterizedTest, @RepeatedTest, @TestFactory или @TestTemplate.
 * Ключи метода - из значений всех его аннотаций: @DisplayName, name у @ParameterizedTest, @Zephyr("...") и любых других
 * (один и тот же ключ в нескольких аннотациях - один ключ). Не считаются: @TmsLink (это цель), источники данных
 * (@...Source), @Disabled..., ссылки Allure на задачи (@Link, @Issue, @Story). Ключ в комментарии не считается.
 * Для dup считаются все ключи метода: из @DisplayName, из name и из @TmsLink. @DisplayName над классом не считается.
 * Файл разбирается по символам: комментарии и строки не путаются с кодом, аннотации могут быть многострочными,
 * с пробелами и переводами строки перед "(", полным именем и на одной строке с объявлением.
 * Последняя строка вывода - всегда "итого: N". Строки до неё - находки; "итого: 0" - находок нет.
 */
public class MarkupKeys {

    private static final Pattern KEY = Pattern.compile("[A-Z][A-Z0-9]*-T[0-9]+");
    private static final Pattern NAME_ARG = Pattern.compile("\\bname\\s*=");
    private static final Pattern NAMED = Pattern.compile("^\\s*[A-Za-z_][A-Za-z0-9_]*\\s*=");
    private static final Pattern SKIP = Pattern.compile(".*Sources?|Disabled.*|Link|Links|Issue|Issues|Story|Stories|SuppressWarnings");
    private static final Pattern VALUE_ARG = Pattern.compile("^\\(\\s*value\\s*=");
    private static final Set<String> TESTS = Set.of("Test", "ParameterizedTest", "RepeatedTest", "TestFactory", "TestTemplate");

    private record Method(String place, String name, Set<String> keys, Set<String> all, boolean hasLink, boolean test,
                          boolean unknown, Set<String> from) {
    }

    public static void main(String[] args) throws IOException {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        if (args.length < 2 || !Set.of("missing", "dup", "count").contains(args[0])) {
            System.out.println("использование: MarkupKeys.java missing|dup|count <каталог тестов>...");
            System.exit(2);
        }
        List<Method> methods = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            List<Path> files;
            try (Stream<Path> walk = Files.walk(Paths.get(args[i]))) {
                files = walk.filter(p -> p.toString().endsWith(".java") || p.toString().endsWith(".kt"))
                        .filter(p -> !p.toString().contains("/target/") && !p.toString().contains("/build/"))
                        .sorted().toList();
            }
            for (Path file : files) {
                methods.addAll(parse(file));
            }
        }
        int found = 0;
        if (args[0].equals("missing")) {
            for (Method m : methods) {
                if (m.test() && m.unknown()) {
                    System.out.println(m.place() + ": " + m.name() + " - значение не разобрать, проверьте вручную");
                    found++;
                } else if (m.test() && !m.keys().isEmpty() && !m.hasLink()) {
                    System.out.println(m.place() + ": " + m.name() + " - " + String.join(" ", m.keys()) + " - нет @TmsLink (из "
                            + String.join(", ", m.from()) + ")");
                    found++;
                }
            }
        } else if (args[0].equals("dup")) {
            Map<String, List<String>> byKey = new TreeMap<>();
            for (Method m : methods) {
                if (!m.test()) {
                    continue;
                }
                for (String key : m.all()) {
                    byKey.computeIfAbsent(key, k -> new ArrayList<>()).add(m.place() + ":" + m.name());
                }
            }
            for (Map.Entry<String, List<String>> e : byKey.entrySet()) {
                if (e.getValue().size() > 1) {
                    System.out.println(e.getKey() + " - " + String.join(" ", e.getValue()));
                    found++;
                }
            }
            for (Method m : methods) {
                if (m.test() && m.unknown()) {
                    System.out.println(m.place() + ":" + m.name() + " - значение не разобрать, проверьте вручную");
                    found++;
                }
            }
        } else {
            long tests = methods.stream().filter(Method::test).count();
            long linked = methods.stream().filter(m -> m.test() && m.hasLink()).count();
            System.out.println("тест-методов: " + tests);
            System.out.println("с @TmsLink: " + linked);
            found = (int) (tests - linked);
            System.out.println("итого без @TmsLink: " + found);
            return;
        }
        System.out.println("итого: " + found);
    }

    /** Разбор файла: аннотации копятся до объявления метода; класс, поле, блок или ";" их сбрасывают. */
    private static List<Method> parse(Path file) throws IOException {
        String text = Files.readString(file, StandardCharsets.UTF_8);
        String code = mask(text, true);
        String noComments = mask(text, false);
        List<Method> result = new ArrayList<>();
        Pending p = new Pending();
        int i = 0;
        int n = code.length();
        while (i < n) {
            char c = code.charAt(i);
            if (c == '@') {
                int j = i + 1;
                int start = j;
                while (j < n && (Character.isJavaIdentifierPart(code.charAt(j)) || code.charAt(j) == '.' || code.charAt(j) == ':')) {
                    j++;
                }
                String name = code.substring(start, j);
                if (name.contains(":")) {
                    name = name.substring(name.lastIndexOf(':') + 1);
                }
                name = name.substring(name.lastIndexOf('.') + 1);
                int k = skipSpace(code, j);
                String argsText = "";
                String argsCode = "";
                if (k < n && code.charAt(k) == '(') {
                    int end = matching(code, k);
                    argsText = noComments.substring(k, end);
                    argsCode = code.substring(k, end);
                    j = end;
                }
                p.add(name, argsText, argsCode);
                i = j;
                continue;
            }
            if (Character.isJavaIdentifierStart(c) && (i == 0 || !Character.isJavaIdentifierPart(code.charAt(i - 1)))) {
                int j = i;
                while (j < n && Character.isJavaIdentifierPart(code.charAt(j))) {
                    j++;
                }
                String word = code.substring(i, j);
                if (word.equals("class") || word.equals("interface") || word.equals("object") || word.equals("enum")) {
                    p = new Pending();
                } else if (word.equals("void") || word.equals("fun")) {
                    int k = skipSpace(code, j);
                    int s = k;
                    if (k < n && code.charAt(k) == '`') {
                        int close = code.indexOf('`', k + 1);
                        k = close < 0 ? n : close + 1;
                    } else {
                        while (k < n && Character.isJavaIdentifierPart(code.charAt(k))) {
                            k++;
                        }
                    }
                    if (k > s) {
                        String method = code.substring(s, k).replace("`", "");
                        int line = 1;
                        for (int q = 0; q < s; q++) {
                            if (text.charAt(q) == '\n') {
                                line++;
                            }
                        }
                        p.declare(file + ":" + line, method, result);
                        p = new Pending();
                        j = k;
                    }
                }
                i = j;
                continue;
            }
            if (c == ';' || c == '{' || c == '}' || c == '=') {
                p = new Pending();
            }
            i++;
        }
        return result;
    }

    private static final class Pending {
        boolean hasLink;
        boolean test;
        boolean unknown;
        Set<String> keys = new LinkedHashSet<>();
        Set<String> from = new LinkedHashSet<>();
        Set<String> linkKeys = new LinkedHashSet<>();

        /** args - текст аргументов без комментариев, code - тот же текст, где строки заменены пробелами. */
        void add(String name, String args, String code) {
            switch (name) {
                case "TmsLink" -> {
                    hasLink = true;
                    if (args.length() > 1) {
                        Matcher v = VALUE_ARG.matcher(code);
                        String text = evaluate(args.substring(v.find() ? v.end() : 1, args.length() - 1));
                        if (text == null) {
                            unknown = true;
                        } else {
                            Matcher m = KEY.matcher(text);
                            while (m.find()) {
                                linkKeys.add(m.group());
                            }
                        }
                    }
                }
                case "TmsLinks" -> {
                    hasLink = true;
                    Matcher m = KEY.matcher(args);
                    while (m.find()) {
                        linkKeys.add(m.group());
                    }
                }
                case "DisplayName" -> value("@DisplayName", args, code);
                case "ParameterizedTest" -> {
                    Matcher m = NAME_ARG.matcher(code);
                    if (m.find()) {
                        int end = m.end();
                        int depth = 0;
                        while (end < code.length() - 1) {
                            char c = code.charAt(end);
                            if (c == '(' || c == '{' || c == '[') {
                                depth++;
                            } else if (c == ')' || c == '}' || c == ']') {
                                depth--;
                            } else if (c == ',' && depth == 0) {
                                break;
                            }
                            end++;
                        }
                        addValue("name у @ParameterizedTest", args.substring(m.end(), end));
                    }
                }
                default -> {
                    if (!SKIP.matcher(name).matches() && args.length() > 1) {
                        other("@" + name, args.substring(1, args.length() - 1), code.substring(1, code.length() - 1));
                    }
                }
            }
            if (TESTS.contains(name)) {
                test = true;
            }
        }

        void declare(String place, String method, List<Method> result) {
            Set<String> all = new LinkedHashSet<>(keys);
            all.addAll(linkKeys);
            if (!all.isEmpty() || test || unknown) {
                result.add(new Method(place, method, keys, all, hasLink, test, unknown, from));
            }
        }

        /** Значение единственного аргумента (или value = ...) аннотации. */
        private void value(String source, String args, String code) {
            if (args.length() < 2) {
                return;
            }
            Matcher v = VALUE_ARG.matcher(code);
            int start = v.find() ? v.end() : 1;
            addValue(source, args.substring(start, args.length() - 1));
        }

        /** Любая другая аннотация: каждый аргумент (и элемент массива) со строкой разбирается отдельно. */
        private void other(String source, String args, String code) {
            int start = 0;
            int depth = 0;
            for (int i = 0; i <= code.length(); i++) {
                char c = i < code.length() ? code.charAt(i) : ',';
                if (c == '(' || c == '{' || c == '[') {
                    depth++;
                } else if (c == ')' || c == '}' || c == ']') {
                    depth--;
                } else if (c == ',' && depth == 0) {
                    String part = args.substring(start, i);
                    String partCode = code.substring(start, i);
                    Matcher named = NAMED.matcher(partCode);
                    if (named.find()) {
                        part = part.substring(named.end());
                        partCode = partCode.substring(named.end());
                    }
                    String trimmed = partCode.strip();
                    int at = partCode.indexOf('@');
                    int paren = partCode.indexOf('(');
                    if (trimmed.startsWith("@") && paren > at) {
                        String inner = partCode.substring(at + 1, paren).strip();
                        inner = inner.substring(inner.lastIndexOf('.') + 1);
                        int close = partCode.lastIndexOf(')');
                        if (!SKIP.matcher(inner).matches() && !inner.startsWith("TmsLink") && close > paren) {
                            other("@" + inner, part.substring(paren + 1, close), partCode.substring(paren + 1, close));
                        }
                    } else if (trimmed.startsWith("{") || trimmed.startsWith("[") || trimmed.startsWith("arrayOf(")) {
                        int open = partCode.indexOf(trimmed.charAt(0) == 'a' ? '(' : trimmed.charAt(0));
                        int close = Math.max(partCode.lastIndexOf('}'), Math.max(partCode.lastIndexOf(']'), partCode.lastIndexOf(')')));
                        if (open >= 0 && close > open) {
                            other(source, part.substring(open + 1, close), partCode.substring(open + 1, close));
                        }
                    } else if (part.contains("\"")) {
                        String text = evaluate(part);
                        if (text != null) {
                            addKeys(source, text);
                        } else if (KEY.matcher(part).find()) {
                            unknown = true;
                        }
                    }
                    start = i + 1;
                }
            }
        }

        /** Ключи из значения выражения. Выражение не из строк и "+" (константа, вызов) - unknown: проверить вручную. */
        private void addValue(String source, String expr) {
            String text = evaluate(expr);
            if (text == null) {
                unknown = true;
                return;
            }
            addKeys(source, text);
        }

        private void addKeys(String source, String text) {
            Matcher m = KEY.matcher(text);
            while (m.find()) {
                keys.add(m.group());
                from.add(source);
            }
        }
    }

    /** Значение константного выражения из строковых литералов и "+"; null - выражение не разобрать. */
    static String evaluate(String expr) {
        StringBuilder out = new StringBuilder();
        int i = 0;
        int n = expr.length();
        boolean any = false;
        while (i < n) {
            char c = expr.charAt(i);
            if (Character.isWhitespace(c) || c == '+') {
                i++;
            } else if (expr.startsWith("\"\"\"", i)) {
                int end = expr.indexOf("\"\"\"", i + 3);
                if (end < 0) {
                    return null;
                }
                out.append(textBlock(expr.substring(i + 3, end)));
                i = end + 3;
                any = true;
            } else if (c == '"') {
                int j = i + 1;
                while (j < n && expr.charAt(j) != '"') {
                    if (expr.charAt(j) == '\\' && j + 1 < n) {
                        char e = expr.charAt(++j);
                        out.append(e == 'n' ? '\n' : e == 't' ? '\t' : e);
                    } else {
                        out.append(expr.charAt(j));
                    }
                    j++;
                }
                if (j >= n) {
                    return null;
                }
                i = j + 1;
                any = true;
            } else {
                return null;
            }
        }
        return any ? out.toString() : null;
    }

    /** Текстовый блок Java: без первой строки после открывающих кавычек и без общего отступа. */
    private static String textBlock(String raw) {
        int nl = raw.indexOf('\n');
        String body = nl >= 0 && raw.substring(0, nl).isBlank() ? raw.substring(nl + 1) : raw;
        String[] lines = body.split("\n", -1);
        int indent = Integer.MAX_VALUE;
        for (String l : lines) {
            if (!l.isBlank() || l == lines[lines.length - 1]) {
                int k = 0;
                while (k < l.length() && Character.isWhitespace(l.charAt(k))) {
                    k++;
                }
                indent = Math.min(indent, k);
            }
        }
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < lines.length; i++) {
            String l = lines[i];
            b.append(l.length() >= indent ? l.substring(indent) : l.strip());
            if (i < lines.length - 1) {
                b.append('\n');
            }
        }
        return b.toString();
    }

    private static int skipSpace(String s, int i) {
        while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
            i++;
        }
        return i;
    }

    /** Индекс после ")", парной к "(" в позиции open. Строки и комментарии уже заменены пробелами. */
    private static int matching(String code, int open) {
        int depth = 0;
        for (int i = open; i < code.length(); i++) {
            char c = code.charAt(i);
            if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) {
                    return i + 1;
                }
            }
        }
        return code.length();
    }

    /** Та же длина и те же переводы строк; комментарии - пробелы, а при strings=true - и строки, текстовые блоки, символы. */
    private static String mask(String t, boolean strings) {
        StringBuilder b = new StringBuilder(t);
        int n = t.length();
        int i = 0;
        while (i < n) {
            if (t.startsWith("//", i)) {
                while (i < n && t.charAt(i) != '\n') {
                    b.setCharAt(i++, ' ');
                }
            } else if (t.startsWith("/*", i)) {
                int end = t.indexOf("*/", i + 2);
                end = end < 0 ? n : end + 2;
                blank(b, t, i, end);
                i = end;
            } else if (t.startsWith("\"\"\"", i)) {
                int end = t.indexOf("\"\"\"", i + 3);
                end = end < 0 ? n : end + 3;
                if (strings) {
                    blank(b, t, i, end);
                }
                i = end;
            } else if (t.charAt(i) == '"' || t.charAt(i) == '\'') {
                char q = t.charAt(i);
                int j = i + 1;
                while (j < n && t.charAt(j) != q && t.charAt(j) != '\n') {
                    j += t.charAt(j) == '\\' ? 2 : 1;
                }
                int end = Math.min(n, j + 1);
                if (strings) {
                    blank(b, t, i, end);
                }
                i = end;
            } else {
                i++;
            }
        }
        return b.toString();
    }

    private static void blank(StringBuilder b, String t, int from, int to) {
        for (int i = from; i < to; i++) {
            if (t.charAt(i) != '\n') {
                b.setCharAt(i, ' ');
            }
        }
    }
}
