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
 * Ключи метода - из его @DisplayName и из name его @ParameterizedTest (один и тот же ключ в обоих - один ключ).
 * Для dup считаются все ключи метода: из @DisplayName, из name и из @TmsLink. @DisplayName над классом не считается.
 * Файл разбирается по символам: комментарии и строки не путаются с кодом, аннотации могут быть многострочными,
 * с пробелами и переводами строки перед "(", полным именем и на одной строке с объявлением.
 * Последняя строка вывода - всегда "итого: N". Строки до неё - находки; "итого: 0" - находок нет.
 */
public class MarkupKeys {

    private static final Pattern KEY = Pattern.compile("[A-Z][A-Z0-9]*-T[0-9]+");
    private static final Set<String> TESTS = Set.of("Test", "ParameterizedTest", "RepeatedTest", "TestFactory", "TestTemplate");

    private record Method(String place, String name, Set<String> keys, Set<String> all, boolean hasLink, boolean test) {
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
                if (!m.keys().isEmpty() && !m.hasLink()) {
                    System.out.println(m.place() + ": " + m.name() + " - " + String.join(" ", m.keys()) + " - нет @TmsLink");
                    found++;
                }
            }
        } else if (args[0].equals("dup")) {
            Map<String, List<String>> byKey = new TreeMap<>();
            for (Method m : methods) {
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
        String code = mask(text);
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
                if (k < n && code.charAt(k) == '(') {
                    int end = matching(code, k);
                    argsText = text.substring(k, end);
                    j = end;
                }
                p.add(name, argsText);
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
        Set<String> displayKeys = new LinkedHashSet<>();
        Set<String> nameKeys = new LinkedHashSet<>();
        Set<String> linkKeys = new LinkedHashSet<>();

        void add(String name, String args) {
            switch (name) {
                case "TmsLink", "TmsLinks" -> {
                    hasLink = true;
                    addKeys(linkKeys, args);
                }
                case "DisplayName" -> addKeys(displayKeys, args);
                case "ParameterizedTest" -> addKeys(nameKeys, args);
                default -> {
                }
            }
            if (TESTS.contains(name)) {
                test = true;
            }
        }

        void declare(String place, String method, List<Method> result) {
            Set<String> keys = new LinkedHashSet<>(displayKeys);
        keys.addAll(nameKeys);
            Set<String> all = new LinkedHashSet<>(displayKeys);
            all.addAll(nameKeys);
            all.addAll(linkKeys);
            if (!all.isEmpty() || test) {
                result.add(new Method(place, method, keys, all, hasLink, test));
            }
        }
    }

    private static void addKeys(Set<String> target, String text) {
        Matcher m = KEY.matcher(text);
        while (m.find()) {
            target.add(m.group());
        }
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

    /** Та же длина и те же переводы строк; содержимое комментариев, строк, текстовых блоков и символов - пробелы. */
    private static String mask(String t) {
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
                blank(b, t, i, end);
                i = end;
            } else if (t.charAt(i) == '"' || t.charAt(i) == '\'') {
                char q = t.charAt(i);
                int j = i + 1;
                while (j < n && t.charAt(j) != q && t.charAt(j) != '\n') {
                    j += t.charAt(j) == '\\' ? 2 : 1;
                }
                int end = Math.min(n, j + 1);
                blank(b, t, i, end);
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
